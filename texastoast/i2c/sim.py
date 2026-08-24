"""In-memory Magma Hub simulator.

You should not need the hardware to build for the hardware. ``SimBus``
implements the smbus2 surface that :class:`~texastoast.i2c.bus.I2CBus` uses,
so injecting it as a backend runs the *entire* real stack — bus, hub protocol
handshake, ``ControllerState`` parsing, input adapters — against simulated
controllers::

    hub, sim = simulated_hub()
    sim.press(BTN_A)
    hub.poll()          # real MagmaHub, real protocol, no wires

The simulator is deliberately strict about the protocol: a block read that was
not preceded by a select-write raises ``OSError``, exactly as the Pico
firmware would refuse it. A sloppier sim that answered any read would keep
passing even if :class:`MagmaHub` stopped sending the select-write — the one
regression this module exists to catch.
"""

from __future__ import annotations

import logging
import threading
import time

from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.protocol import (
    BTN_A,
    BTN_B,
    BTN_DOWN,
    BTN_LEFT,
    BTN_RIGHT,
    BTN_SELECT,
    BTN_START,
    BTN_UP,
    CONTROLLER_SIZE,
    ControllerState,
)

logger = logging.getLogger(__name__)


class _SimHub:
    """One simulated hub: a flat controller memory plus a read window."""

    def __init__(self, num_controllers: int):
        self.num_controllers = num_controllers
        self.memory = bytearray(num_controllers * CONTROLLER_SIZE)
        self.connected = True
        # (start_addr, num_bytes) armed by the select-write, consumed by the
        # following block read. One-shot, like the firmware's read pointer.
        self.window: tuple[int, int] | None = None


class SimBus:
    """smbus2-compatible backend simulating one or more Magma Hubs.

    Pass as ``I2CBus(backend=SimBus(...))``. ``hubs`` maps I2C address to
    controller count; the default is one hub at 0x08 with one controller.

    All methods are thread-safe: a :class:`~texastoast.i2c.poller.HubPoller`
    may be reading on its thread while test code or a
    :class:`KeyboardHubDriver` writes controller state from another.
    """

    def __init__(self, hubs: dict[int, int] | None = None):
        if hubs is None:
            hubs = {0x08: 1}
        self._hubs = {addr: _SimHub(n) for addr, n in hubs.items()}
        self._lock = threading.Lock()
        self._fail_reads = 0
        self._read_delay = 0.0
        self._closed = False

    # ── smbus2 surface ──────────────────────────────────────────────

    def read_byte(self, address: int) -> int:
        with self._lock:
            self._check_read(address)
            return 0

    def read_byte_data(self, address: int, register: int) -> int:
        with self._lock:
            self._check_read(address)
            hub = self._hubs[address]
            if not 0 <= register < len(hub.memory):
                raise OSError(f"sim: register 0x{register:02x} out of range")
            return hub.memory[register]

    def write_byte_data(self, address: int, register: int, value: int):
        with self._lock:
            self._require_hub(address)

    def read_i2c_block_data(self, address: int, register: int,
                            length: int) -> list[int]:
        delay = self._read_delay
        if delay > 0:
            time.sleep(delay)
        with self._lock:
            self._check_read(address)
            hub = self._hubs[address]
            if hub.window is None:
                raise OSError(
                    "sim: block read with no preceding select-write — the "
                    "firmware requires write [start_addr, [num_bytes]] first"
                )
            start, num = hub.window
            hub.window = None
            end = start + min(length, num)
            if end > len(hub.memory):
                raise OSError(f"sim: read past controller memory (0x{end:02x})")
            return list(hub.memory[start:end])

    def write_i2c_block_data(self, address: int, register: int, data: list[int]):
        with self._lock:
            self._require_hub(address)
            hub = self._hubs[address]
            # The select-write: register is the start address, data[0] the
            # number of bytes the next read will fetch.
            if len(data) != 1:
                raise OSError(f"sim: malformed select-write {data!r}")
            hub.window = (register, int(data[0]))

    def close(self):
        self._closed = True

    # ── simulation controls ─────────────────────────────────────────

    def set_controller(self, hub_addr: int, index: int, state: ControllerState):
        self.set_buttons(hub_addr, index, state.buttons)
        self.set_joystick(hub_addr, index, state.joystick)

    def set_buttons(self, hub_addr: int, index: int, buttons: int):
        with self._lock:
            hub = self._hubs[hub_addr]
            hub.memory[index * CONTROLLER_SIZE] = buttons & 0xFF

    def set_joystick(self, hub_addr: int, index: int, joystick: int):
        with self._lock:
            hub = self._hubs[hub_addr]
            hub.memory[index * CONTROLLER_SIZE + 1] = joystick & 0xFF

    def press(self, button_mask: int, hub_addr: int = 0x08, index: int = 0):
        with self._lock:
            hub = self._hubs[hub_addr]
            hub.memory[index * CONTROLLER_SIZE] |= button_mask & 0xFF

    def release(self, button_mask: int, hub_addr: int = 0x08, index: int = 0):
        with self._lock:
            hub = self._hubs[hub_addr]
            hub.memory[index * CONTROLLER_SIZE] &= ~button_mask & 0xFF

    def fail_next_reads(self, n: int):
        """Make the next ``n`` reads raise ``OSError`` — a loose wire, on demand."""
        with self._lock:
            self._fail_reads = n

    def set_read_delay(self, seconds: float):
        """Add latency to every block read, for exercising non-blocking paths."""
        self._read_delay = seconds

    def disconnect_hub(self, hub_addr: int):
        """Reads at ``hub_addr`` raise until :meth:`reconnect_hub`."""
        with self._lock:
            self._hubs[hub_addr].connected = False

    def reconnect_hub(self, hub_addr: int):
        with self._lock:
            self._hubs[hub_addr].connected = True

    def play_recording(self, path, hub_addr: int = 0x08, index: int = 0):
        """A driver that feeds a ``.ttrec`` recording into this sim.

        Call ``advance(dt)`` once per frame; the recorded raw bytes are
        written into controller memory at the recorded times, so the full
        stack — protocol, :class:`MagmaHub`, ``MagmaHubInput`` — replays the
        session exactly as the hardware produced it.
        """
        from texastoast.input.recording import load_events
        return ReplayDriver(self, load_events(path), hub_addr=hub_addr, index=index)

    # ── internals ───────────────────────────────────────────────────

    def _require_hub(self, address: int):
        if self._closed:
            raise OSError("sim: bus is closed")
        if address not in self._hubs:
            raise OSError(f"sim: no device at 0x{address:02x}")

    def _check_read(self, address: int):
        self._require_hub(address)
        if self._fail_reads > 0:
            self._fail_reads -= 1
            raise OSError("sim: injected read failure")
        if not self._hubs[address].connected:
            raise OSError(f"sim: hub 0x{address:02x} is disconnected")


class ReplayDriver:
    """Steps a recorded event list into a :class:`SimBus`. See
    :meth:`SimBus.play_recording`."""

    def __init__(self, sim: SimBus, events: list[dict],
                 hub_addr: int = 0x08, index: int = 0):
        self._sim = sim
        self._events = events
        self._hub_addr = hub_addr
        self._index = index
        self._t = 0.0
        self._cursor = 0

    @property
    def finished(self) -> bool:
        return self._cursor >= len(self._events)

    def advance(self, dt: float):
        """Advance the virtual clock and apply every event now due."""
        self._t += dt
        while self._cursor < len(self._events):
            event = self._events[self._cursor]
            if event["t"] > self._t:
                break
            if "buttons" in event:
                self._sim.set_buttons(self._hub_addr, self._index, event["buttons"])
            if "joystick" in event:
                self._sim.set_joystick(self._hub_addr, self._index, event["joystick"])
            self._cursor += 1


def simulated_hub(num_controllers: int = 1,
                  address: int = 0x08) -> tuple[MagmaHub, SimBus]:
    """A real :class:`MagmaHub` on a real :class:`I2CBus` over a :class:`SimBus`.

    The one-line wiring for examples and tests::

        hub, sim = simulated_hub()
        sim.press(BTN_A)
        assert hub.poll()[0].a
    """
    sim = SimBus({address: num_controllers})
    bus = I2CBus(backend=sim)
    hub = MagmaHub(address, bus, num_controllers=num_controllers, poll_interval=0.0)
    return hub, sim


class KeyboardHubDriver:
    """Turns a keyboard into a simulated controller.

    Binds the engine's standard key map on ``root`` and writes the resulting
    button byte into ``sim`` each time :meth:`apply` is called (once per
    frame). This is what lets the test bench — and any game — run "hardware"
    input on a machine with no I2C at all.

    tkinter is imported lazily here so ``texastoast.i2c`` stays importable on
    headless systems.
    """

    _KEY_MAP = {
        "Up": BTN_UP, "w": BTN_UP, "W": BTN_UP,
        "Down": BTN_DOWN, "s": BTN_DOWN, "S": BTN_DOWN,
        "Left": BTN_LEFT, "a": BTN_LEFT, "A": BTN_LEFT,
        "Right": BTN_RIGHT, "d": BTN_RIGHT, "D": BTN_RIGHT,
        "z": BTN_A, "Z": BTN_A, "Return": BTN_A,
        "x": BTN_B, "X": BTN_B, "BackSpace": BTN_B,
        "Escape": BTN_START, "p": BTN_START, "P": BTN_START,
        "Shift_L": BTN_SELECT, "Shift_R": BTN_SELECT,
    }

    def __init__(self, root, sim: SimBus, hub_addr: int = 0x08, index: int = 0):
        import tkinter as tk  # noqa: F401 — lazy: headless imports must survive

        self._root = root
        self._sim = sim
        self._hub_addr = hub_addr
        self._index = index
        # Same shape as KeyboardInput: several keys share a button, so track
        # which keys hold each mask down rather than a single bool.
        self._held: dict[int, set[str]] = {}
        self._buttons = 0
        self._bindings: list[tuple[str, str]] = []

        for key, mask in self._KEY_MAP.items():
            press_seq = f"<KeyPress-{key}>"
            release_seq = f"<KeyRelease-{key}>"
            press_id = root.bind(press_seq, lambda e, k=key, m=mask: self._press(k, m), add="+")
            release_id = root.bind(release_seq, lambda e, k=key, m=mask: self._release(k, m), add="+")
            self._bindings.append((press_seq, press_id))
            self._bindings.append((release_seq, release_id))

    def _press(self, key: str, mask: int):
        self._held.setdefault(mask, set()).add(key)
        self._buttons |= mask

    def _release(self, key: str, mask: int):
        keys = self._held.get(mask)
        if keys is not None:
            keys.discard(key)
        if not keys:
            self._buttons &= ~mask & 0xFF

    def apply(self):
        """Write the current button byte into the sim. Call once per frame."""
        self._sim.set_buttons(self._hub_addr, self._index, self._buttons)

    def destroy(self):
        for sequence, funcid in self._bindings:
            try:
                self._root.unbind(sequence, funcid)
            except Exception:
                pass
        self._bindings.clear()
        self._held.clear()
        self._buttons = 0
