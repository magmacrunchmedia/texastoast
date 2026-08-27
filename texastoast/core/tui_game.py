"""Textual host for the engine — the terminal counterpart to :class:`Game`.

This is the only module in texastoast that imports Textual, and it is imported
lazily (see :mod:`texastoast.core`), so the package keeps its zero required
dependencies. Install with the ``tui`` extra to use it::

    pip install "texastoast[tui]"

Three pieces live here:

* :class:`TextualScheduler` — ``after``/``after_cancel`` over Textual's timers,
  which is the entire adaptation :class:`~texastoast.core.loop.GameLoop` needs.
* :class:`GameSurface` — one Textual widget that paints a
  :class:`~texastoast.render.cellbuffer.CellBuffer`. Deliberately a *single*
  widget rather than a tree: a game repaints everything every frame, so
  Textual's reactive per-widget diffing has nothing to offer it and would only
  add overhead.
* :class:`TuiGame` — mirrors :class:`Game`'s public API so a game's wiring code
  reads the same on either backend.

:class:`TuiGame` takes its surface and scheduler by injection. Nothing below
``TuiGame`` knows what Textual is, so the planned hand-written ANSI backend
becomes a different pair of constructor arguments rather than a second engine.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from rich.segment import Segment
from rich.style import Style
from textual import events
from textual.app import App, ComposeResult
from textual.strip import Strip
from textual.widget import Widget

from texastoast.core.config import DEFAULT_CONFIG, Config
from texastoast.core.loop import GameLoop
from texastoast.input.abstract import InputState
from texastoast.render.cellbuffer import CellBuffer
from texastoast.render.tui import TuiRenderer

logger = logging.getLogger(__name__)

#: Fallback terminal size, used only until the real one is known.
DEFAULT_COLS = 80
DEFAULT_ROWS = 24


class TextualScheduler:
    """Satisfies :class:`~texastoast.core.scheduler.Scheduler` using Textual timers.

    Textual measures delays in seconds and returns a ``Timer`` object; the loop
    speaks milliseconds and treats the handle as opaque. That mismatch is the
    whole of this class.
    """

    def __init__(self, app: App):
        self._app = app

    def after(self, ms: int, fn: Callable[[], Any]) -> Any:
        return self._app.set_timer(max(0, ms) / 1000.0, fn)

    def after_cancel(self, handle: Any) -> None:
        if handle is None:
            return
        try:
            handle.stop()
        except Exception:
            # The timer may already have fired, or the app may be tearing down.
            # The loop cancels without checking, so this must be tolerant.
            logger.debug("Ignoring failure to cancel a Textual timer", exc_info=True)


class GameSurface(Widget):
    """Paints a :class:`CellBuffer` — one widget, filling the screen.

    ``flush`` is the surface half of the contract
    :meth:`~texastoast.render.tui.TuiRenderer.present` calls: it takes the
    finished frame and asks Textual to repaint.
    """

    DEFAULT_CSS = """
    GameSurface {
        width: 100%;
        height: 100%;
    }
    """

    can_focus = True

    def __init__(self, buffer: CellBuffer | None = None, **kwargs):
        super().__init__(**kwargs)
        self._buffer = buffer if buffer is not None else CellBuffer(DEFAULT_COLS, DEFAULT_ROWS)
        self._on_resize: Callable[[int, int], None] | None = None
        #: Styles are rebuilt from hex on every cell otherwise; games reuse a
        #: small palette, so caching turns per-cell allocation into a dict hit.
        self._style_cache: dict[tuple[str | None, str | None], Style] = {}

    @property
    def buffer(self) -> CellBuffer:
        return self._buffer

    def set_resize_handler(self, fn: Callable[[int, int], None]) -> None:
        self._on_resize = fn

    def flush(self, buffer: CellBuffer) -> None:
        """Adopt the finished frame and schedule a repaint.

        The buffer is kept by reference, not copied. That is safe because
        everything here runs on Textual's single event-loop thread: the repaint
        happens after the current callback returns and before the next tick can
        start clearing the buffer for the following frame.
        """
        self._buffer = buffer
        self.refresh()

    def on_resize(self, event: events.Resize) -> None:
        if self._on_resize is not None:
            self._on_resize(event.size.width, event.size.height)

    def _style_for(self, fg: str | None, bg: str | None) -> Style:
        key = (fg, bg)
        style = self._style_cache.get(key)
        if style is None:
            style = Style(color=fg or None, bgcolor=bg or None)
            self._style_cache[key] = style
        return style

    def render_line(self, y: int) -> Strip:
        """Build one line, coalescing runs of identical style into segments.

        One Segment per cell would work but makes Textual's compositor do
        width-by-width work over thousands of single-character segments each
        frame. Games paint in blocks, so runs are usually long.
        """
        cells = self._buffer.row(y)
        if not cells:
            return Strip.blank(self.size.width)

        segments: list[Segment] = []
        run: list[str] = []
        run_key: tuple[str | None, str | None] | None = None

        for cell in cells:
            key = (cell.fg, cell.bg)
            if key != run_key:
                if run:
                    segments.append(Segment("".join(run), self._style_for(*run_key)))
                run = []
                run_key = key
            run.append(cell.char)
        if run:
            segments.append(Segment("".join(run), self._style_for(*run_key)))

        return Strip(segments, len(cells))


class TuiInput:
    """Keyboard input from a terminal, as an
    :class:`~texastoast.input.abstract.InputSource`.

    Terminals report key *presses* and never releases, so held state cannot be
    observed the way :mod:`texastoast.input.keyboard` observes it under tkinter.
    Two modes cover the difference:

    ``hold_ms = 0`` (the default) — **edge** semantics. A press sets the button
    for exactly one :meth:`poll`, then clears. This is what a turn-based game
    wants, and it is honest: one keystroke, one action.

    ``hold_ms > 0`` — **decay** semantics. A press keeps the button set for that
    long, refreshed by the terminal's own key-repeat. This approximates holding
    a key for real-time games. Tune it above the terminal's repeat interval
    (typically 30-50 ms) or the input will stutter.
    """

    #: Terminal key names to controller buttons. WASD sits alongside the arrows;
    #: note ``a``/``s``/``d`` are directions here, while the *button* named "a"
    #: is space/enter/z, as on a gamepad.
    KEY_MAP: dict[str, str] = {
        "up": "up", "w": "up", "k": "up",
        "down": "down", "s": "down", "j": "down",
        "left": "left", "a": "left", "h": "left",
        "right": "right", "d": "right", "l": "right",
        "space": "a", "enter": "a", "z": "a",
        "x": "b", "backspace": "b",
        "tab": "select",
        "p": "start",
    }

    def __init__(self, hold_ms: int = 0, clock: Callable[[], float] | None = None):
        import time

        self.hold_ms = hold_ms
        self._clock = clock or (lambda: time.monotonic() * 1000.0)
        self._held: dict[str, float] = {}
        self._edge: set[str] = set()
        self._pending: list[str] = []

    # ── Feeding ─────────────────────────────────────────────────────

    def press(self, key: str) -> None:
        """Record a key press. Called by the app for every key event."""
        self._pending.append(key)
        button = self.KEY_MAP.get(key)
        if button is None:
            return
        self._edge.add(button)
        self._held[button] = self._clock()

    # ── InputSource ─────────────────────────────────────────────────

    def poll(self) -> InputState:
        state = InputState()
        for button in self._active():
            setattr(state, button, True)
        self._edge.clear()
        return state

    def is_pressed(self, button: str) -> bool:
        return button in self._active()

    def _active(self) -> set[str]:
        if self.hold_ms <= 0:
            return set(self._edge)
        cutoff = self._clock() - self.hold_ms
        expired = [b for b, at in self._held.items() if at < cutoff]
        for button in expired:
            del self._held[button]
        return set(self._held) | self._edge

    # ── Discrete keys ───────────────────────────────────────────────
    #
    # What a turn-based game actually reads: the exact keys pressed since the
    # last frame, including ones with no controller mapping (digits, letters,
    # "escape"). Held-state polling cannot express "the player typed 3".

    def drain(self) -> list[str]:
        """Take every key pressed since the last call, in order."""
        keys, self._pending = self._pending, []
        return keys

    def clear(self) -> None:
        self._pending.clear()
        self._edge.clear()
        self._held.clear()


class _GameApp(App):
    """The Textual application shell. Owns nothing; forwards to :class:`TuiGame`."""

    CSS = """
    Screen {
        background: $surface;
    }
    """

    def __init__(self, game: TuiGame, surface: GameSurface):
        super().__init__()
        self._game = game
        self._surface = surface

    def compose(self) -> ComposeResult:
        yield self._surface

    def on_mount(self) -> None:
        self._surface.focus()
        self._game._on_app_ready(self)

    def on_key(self, event: events.Key) -> None:
        self._game._on_key(event.key)


class TuiGame:
    """Runs a game in the terminal. The counterpart to :class:`Game`.

    The public surface deliberately matches :class:`Game` — ``set_update``,
    ``set_render``, ``start``, ``quit``, ``bind_key``, ``on_close`` — so a
    game's wiring differs only in which class it constructs.

    ``width``/``height`` are **character cells**, not pixels. With
    ``auto_size`` (the default) they are only the size used before the terminal
    reports its own, after which the renderer follows the real terminal.
    """

    def __init__(
        self,
        title: str = DEFAULT_CONFIG.title,
        width: int = DEFAULT_COLS,
        height: int = DEFAULT_ROWS,
        fps: int = DEFAULT_CONFIG.fps,
        config: Config | None = None,
        *,
        auto_size: bool = True,
        surface: GameSurface | None = None,
        scheduler: Any | None = None,
        input_source: TuiInput | None = None,
        max_consecutive_errors: int = 10,
    ):
        self.config = config or Config(title=title, width=width, height=height, fps=fps)
        self._auto_size = auto_size
        self._max_consecutive_errors = max_consecutive_errors

        self._buffer = CellBuffer(width, height)
        self._surface = surface if surface is not None else GameSurface(self._buffer)
        self._renderer = TuiRenderer(width, height, surface=self._surface,
                                     buffer=self._buffer)
        self.input = input_source if input_source is not None else TuiInput()

        self._injected_scheduler = scheduler
        self._app: _GameApp | None = None
        self._loop: GameLoop | None = None
        self._update_fn: Callable[[float], None] | None = None
        self._render_fn: Callable[[], None] | None = None
        self._key_bindings: dict[str, list[Callable[[str], None]]] = {}
        self._teardown: list[Callable[[], None]] = []
        self._loop_error: BaseException | None = None

        self._surface.set_resize_handler(self._on_resize)

    # ── Accessors ───────────────────────────────────────────────────

    @property
    def renderer(self) -> TuiRenderer:
        return self._renderer

    @property
    def surface(self) -> GameSurface:
        return self._surface

    @property
    def app(self) -> _GameApp | None:
        return self._app

    @property
    def loop(self) -> GameLoop | None:
        return self._loop

    def set_update(self, fn: Callable[[float], None]) -> None:
        self._update_fn = fn

    def set_render(self, fn: Callable[[], None]) -> None:
        self._render_fn = fn

    def on_close(self, fn: Callable[[], None]) -> None:
        """Register a cleanup callback to run on :meth:`quit`."""
        self._teardown.append(fn)

    # ── Keys ────────────────────────────────────────────────────────

    def bind_key(self, key: str, callback: Callable[[str], None]) -> None:
        """Bind a key by name, e.g. ``"left"``, ``"space"``, ``"q"``.

        tkinter sequences (``"<Left>"``) are accepted and normalized, so a game
        ported from the canvas backend does not have to rewrite every binding.
        The callback receives the key name; :class:`Game` passes a tkinter
        event, but no game can use both backends' event objects anyway, and a
        name is the part that means the same thing on each.
        """
        self._key_bindings.setdefault(self._normalize_key(key), []).append(callback)

    @staticmethod
    def _normalize_key(key: str) -> str:
        """``"<Left>"`` -> ``"left"``, ``"<KeyPress-a>"`` -> ``"a"``."""
        k = key.strip()
        if k.startswith("<") and k.endswith(">"):
            k = k[1:-1]
        for prefix in ("KeyPress-", "KeyRelease-", "Key-"):
            if k.startswith(prefix):
                k = k[len(prefix):]
        return k.lower()

    def _on_key(self, key: str) -> None:
        self.input.press(key)
        for callback in self._key_bindings.get(key, ()):
            try:
                callback(key)
            except Exception:
                logger.exception("Exception in key binding for %r", key)

    # ── Lifecycle ───────────────────────────────────────────────────

    def _on_resize(self, cols: int, rows: int) -> None:
        if not self._auto_size:
            return
        self._renderer.resize(cols, rows)
        self.config.width = self._renderer.width
        self.config.height = self._renderer.height

    def _on_app_ready(self, app: _GameApp) -> None:
        """Start the game loop once Textual is up and the surface has a size."""
        scheduler = self._injected_scheduler or TextualScheduler(app)
        update = self._update_fn or (lambda dt: None)
        render = self._render_fn or (lambda: None)
        self._loop_error = None
        self._loop = GameLoop(
            scheduler, update, render, self.config.fps,
            max_consecutive_errors=self._max_consecutive_errors,
            on_error=self._on_loop_error,
        )
        self._loop.start()

    def start(self) -> None:
        """Run the terminal app, blocking until the game quits.

        Mirrors :meth:`Game.start`, including re-raising an exception that
        killed the loop — Textual, like tkinter, swallows exceptions raised
        inside a timer callback, so without this the game would exit silently.
        """
        self._app = _GameApp(self, self._surface)
        self._app.run()

        if self._loop_error is not None:
            error, self._loop_error = self._loop_error, None
            raise error

    def _on_loop_error(self, exc: BaseException) -> None:
        self._loop_error = exc
        self.quit()

    def quit(self) -> None:
        if self._loop:
            self._loop.stop()

        for fn in self._teardown:
            try:
                fn()
            except Exception:
                logger.exception("Exception in teardown callback")
        self._teardown.clear()

        if self._app is not None:
            try:
                self._app.exit()
            except Exception:
                logger.debug("Ignoring failure to exit the Textual app", exc_info=True)


__all__ = ["TuiGame", "GameSurface", "TuiInput", "TextualScheduler",
           "DEFAULT_COLS", "DEFAULT_ROWS"]
