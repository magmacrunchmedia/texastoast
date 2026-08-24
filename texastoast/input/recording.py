"""Input recording and replay — the ``.ttrec`` format.

A recording is JSON Lines: a header line, then one line per state *change*::

    {"format": "ttrec", "version": 1, "created": "...", "source": "..."}
    {"t": 1.234, "buttons": 8}
    {"t": 1.401, "buttons": 24, "joystick": 128}

``t`` is seconds since the recording started. Lines are delta-encoded — a
line appears only when something changed, and an omitted key means
"unchanged" — so an idle-heavy session stays tiny. JSONL is append-only:
a session that crashes mid-game still leaves a readable file.

Buttons are stored as the I2C protocol's ``BTN_*`` bitmask, not as engine
field names. That one choice makes the format serve both worlds: decoded to
:class:`InputState` it replays through the engine
(:class:`ReplayInput`), and fed raw into a
:class:`~texastoast.i2c.sim.SimBus` it replays through the full hardware
stack (``SimBus.play_recording``) — which is how a session recorded against
real firmware becomes a regression test.
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from texastoast.i2c.protocol import (
    BTN_A,
    BTN_B,
    BTN_DOWN,
    BTN_LEFT,
    BTN_RIGHT,
    BTN_SELECT,
    BTN_START,
    BTN_UP,
)
from texastoast.input.abstract import InputSource, InputState

FORMAT_NAME = "ttrec"
FORMAT_VERSION = 1

_BUTTON_MASKS = {
    "up": BTN_UP,
    "down": BTN_DOWN,
    "left": BTN_LEFT,
    "right": BTN_RIGHT,
    "a": BTN_A,
    "b": BTN_B,
    "start": BTN_START,
    "select": BTN_SELECT,
}


def encode_buttons(state: InputState) -> int:
    """Pack an :class:`InputState` into the protocol's button bitmask."""
    buttons = 0
    for name, mask in _BUTTON_MASKS.items():
        if getattr(state, name):
            buttons |= mask
    return buttons


def decode_buttons(buttons: int) -> InputState:
    """Unpack a protocol button bitmask into an :class:`InputState`."""
    return InputState(**{
        name: bool(buttons & mask) for name, mask in _BUTTON_MASKS.items()
    })


def load_events(path: str | Path) -> list[dict]:
    """Read a ``.ttrec`` file and return its event lines, sorted by time."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError(f"{path}: empty recording")
    header = json.loads(lines[0])
    if header.get("format") != FORMAT_NAME:
        raise ValueError(f"{path}: not a {FORMAT_NAME} file")
    if header.get("version", 0) > FORMAT_VERSION:
        raise ValueError(
            f"{path}: version {header['version']} is newer than "
            f"this engine understands ({FORMAT_VERSION})"
        )
    events = [json.loads(line) for line in lines[1:] if line.strip()]
    events.sort(key=lambda e: e["t"])
    return events


class InputRecorder:
    """A transparent :class:`InputSource` wrapper that records what flows through.

    Sits anywhere in the input chain — around a ``KeyboardInput``, a
    ``MagmaHubInput``, or a whole ``CompositeInput``; ``poll()`` delegates
    and appends a line whenever the encoded state changed. With a ``path``
    each change is written (and flushed) immediately; without one the events
    stay in memory until :meth:`save`.

    Wire teardown into the game's lifecycle::

        recorder = InputRecorder(source, "session.ttrec")
        recorder.start()
        game.on_close(recorder.stop)
    """

    def __init__(self, source: InputSource, path: str | Path | None = None):
        self._source = source
        self._path = Path(path) if path is not None else None
        self._file = None
        self._events: list[dict] = []
        self._t0: float | None = None
        # The implicit starting state: all released. A fully idle session
        # therefore records no event lines at all.
        self._last_buttons = 0

    @property
    def recording(self) -> bool:
        return self._t0 is not None

    @property
    def events(self) -> list[dict]:
        return list(self._events)

    def start(self):
        """Begin recording. ``t=0`` is now."""
        if self.recording:
            return
        self._events = []
        self._last_buttons = 0
        self._t0 = time.monotonic()
        if self._path is not None:
            self._file = self._path.open("w", encoding="utf-8")
            self._write_line(self._header())

    def stop(self):
        """Stop recording and close the file. Safe to call more than once."""
        self._t0 = None
        if self._file is not None:
            self._file.close()
            self._file = None

    def save(self, path: str | Path):
        """Write the in-memory events out as a complete ``.ttrec`` file."""
        with Path(path).open("w", encoding="utf-8") as f:
            f.write(json.dumps(self._header()) + "\n")
            for event in self._events:
                f.write(json.dumps(event) + "\n")

    # ── InputSource surface ─────────────────────────────────────────

    def poll(self) -> InputState:
        state = self._source.poll()
        if self.recording:
            buttons = encode_buttons(state)
            if buttons != self._last_buttons:
                self._last_buttons = buttons
                event = {"t": round(time.monotonic() - self._t0, 4),
                         "buttons": buttons}
                self._events.append(event)
                self._write_line(event)
        return state

    def is_pressed(self, button: str) -> bool:
        return self._source.is_pressed(button)

    # ── internals ───────────────────────────────────────────────────

    def _header(self) -> dict:
        return {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source": type(self._source).__name__,
        }

    def _write_line(self, obj: dict):
        if self._file is not None:
            self._file.write(json.dumps(obj) + "\n")
            # Flushed per event so a crashed session still leaves the file
            # complete up to its last change. Events only occur on change,
            # so this is cheap.
            self._file.flush()


class ReplayInput:
    """Plays a ``.ttrec`` back as an :class:`InputSource`.

    Two clocks, mutually exclusive:

    * **wall clock** — call :meth:`start`; ``poll()`` returns the state at
      ``now - t0``. For watching a session replay in a live game.
    * **manual** — call :meth:`advance` (or :meth:`seek`) yourself; the real
      clock is never consulted. Two runs with the same ``advance`` calls
      produce the same state sequence — this is the deterministic-test mode.

    After the last event the final state is held and :attr:`finished` is
    True; ``loop=True`` wraps around instead.
    """

    def __init__(self, path_or_events: str | Path | list[dict],
                 loop: bool = False):
        if isinstance(path_or_events, (str, Path)):
            self._events = load_events(path_or_events)
        else:
            self._events = sorted(path_or_events, key=lambda e: e["t"])
        self._loop = loop
        self._t: float = 0.0
        self._t0: float | None = None
        self._cursor = 0
        self._state = InputState()
        self._manual = False

    @property
    def duration(self) -> float:
        return self._events[-1]["t"] if self._events else 0.0

    @property
    def finished(self) -> bool:
        return not self._loop and self._cursor >= len(self._events)

    def start(self):
        """Enter wall-clock mode; ``t=0`` is now."""
        if self._manual:
            raise RuntimeError("ReplayInput is in manual mode (advance/seek was called)")
        self._t0 = time.monotonic()

    def advance(self, dt: float):
        """Step the virtual clock forward. Enters manual mode."""
        if self._t0 is not None:
            raise RuntimeError("ReplayInput is in wall-clock mode (start was called)")
        self._manual = True
        self._t += dt

    def seek(self, t: float):
        """Jump the virtual clock to ``t``. Enters manual mode."""
        if self._t0 is not None:
            raise RuntimeError("ReplayInput is in wall-clock mode (start was called)")
        self._manual = True
        if t < self._t:
            # The cursor only moves forward; rewinding replays from the top.
            self._cursor = 0
            self._state = InputState()
        self._t = t

    # ── InputSource surface ─────────────────────────────────────────

    def poll(self) -> InputState:
        t = self._t
        if self._t0 is not None:
            t = time.monotonic() - self._t0
        self._apply_until(t)
        return replace(self._state)

    def is_pressed(self, button: str) -> bool:
        return getattr(self._state, button, False)

    # ── internals ───────────────────────────────────────────────────

    def _apply_until(self, t: float):
        while True:
            while self._cursor < len(self._events):
                event = self._events[self._cursor]
                if event["t"] > t:
                    return
                if "buttons" in event:
                    self._state = decode_buttons(event["buttons"])
                self._cursor += 1

            if not self._loop or self.duration <= 0:
                return
            # Wrap: shift the clock back one period and replay from the top.
            t -= self.duration
            self._t = t
            if self._t0 is not None:
                self._t0 += self.duration
            self._cursor = 0
            self._state = InputState()
