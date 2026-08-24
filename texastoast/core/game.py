from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable

from texastoast.core.config import DEFAULT_CONFIG, Config
from texastoast.core.loop import GameLoop

logger = logging.getLogger(__name__)


class Game:
    """Main game class. Manages the tkinter window and game lifecycle."""

    def __init__(
        self,
        title: str = DEFAULT_CONFIG.title,
        width: int = DEFAULT_CONFIG.width,
        height: int = DEFAULT_CONFIG.height,
        fps: int = DEFAULT_CONFIG.fps,
        config: Config | None = None,
        root: tk.Misc | None = None,
        max_consecutive_errors: int = 10,
    ):
        """Create the game window.

        ``root`` accepts an existing tkinter root or frame to build into, for
        embedding the game in a larger app or for tests. When omitted a new
        ``Tk`` window is created and owned by this Game.

        ``max_consecutive_errors`` is how many back-to-back failing frames the
        loop tolerates before it stops the game and re-raises from
        :meth:`start`; 0 disables the cutoff and restores the old
        log-and-continue behaviour.
        """
        self.config = config or Config(title=title, width=width, height=height, fps=fps)
        self._max_consecutive_errors = max_consecutive_errors
        self._owns_root = root is None
        self._root = root if root is not None else tk.Tk()
        if self._owns_root:
            self._root.title(self.config.title)
            self._root.resizable(False, False)

        self.canvas = tk.Canvas(
            self._root,
            width=self.config.width,
            height=self.config.height,
            bg=self.config.bg_color,
            highlightthickness=0,
        )
        self.canvas.pack()

        self._loop: GameLoop | None = None
        self._update_fn: Callable[[float], None] | None = None
        self._render_fn: Callable[[], None] | None = None
        self._teardown: list[Callable[[], None]] = []
        self._loop_error: BaseException | None = None

        # Without this, closing the window with the X button leaves the loop
        # running with a pending after() callback. Applies to any window with a
        # close button, not just one we created; an embedded Frame has no
        # protocol() and needs no handler.
        if hasattr(self._root, "protocol"):
            self._root.protocol("WM_DELETE_WINDOW", self.quit)

    @property
    def root(self) -> tk.Misc:
        return self._root

    @property
    def loop(self) -> GameLoop | None:
        return self._loop

    def set_update(self, fn: Callable[[float], None]):
        self._update_fn = fn

    def set_render(self, fn: Callable[[], None]):
        self._render_fn = fn

    def start(self):
        """Start the loop and block in the tkinter main loop.

        When an external ``root`` was supplied the caller owns the main loop,
        so only the game loop is started here.
        """
        update = self._update_fn or (lambda dt: None)
        render = self._render_fn or (lambda: None)
        self._loop_error = None
        self._loop = GameLoop(
            self._root, update, render, self.config.fps,
            max_consecutive_errors=self._max_consecutive_errors,
            on_error=self._on_loop_error,
        )
        self._loop.start()
        if self._owns_root:
            self._root.mainloop()

        # tkinter swallows exceptions raised inside an after() callback, so a
        # broken update() would otherwise end the game with no indication of
        # why. Carrying it out here is what lets a caller — a test, or a script
        # host like magmascript — report it against its own source.
        if self._loop_error is not None:
            error, self._loop_error = self._loop_error, None
            raise error

    def _on_loop_error(self, exc: BaseException):
        self._loop_error = exc
        self.quit()

    def on_close(self, fn: Callable[[], None]):
        """Register a cleanup callback to run on :meth:`quit`.

        Useful for input sources and other objects holding tkinter bindings,
        e.g. ``game.on_close(keyboard.destroy)``.
        """
        self._teardown.append(fn)

    def quit(self):
        if self._loop:
            self._loop.stop()

        for fn in self._teardown:
            try:
                fn()
            except Exception:
                logger.exception("Exception in teardown callback")
        self._teardown.clear()

        # A root we did not create belongs to the caller; leave it standing.
        if not self._owns_root:
            return

        try:
            self._root.quit()
            self._root.destroy()
        except tk.TclError:
            pass

    def bind_key(self, key: str, callback: Callable):
        self._root.bind(key, callback)

    def bind_key_release(self, key: str, callback: Callable):
        if key.startswith("<") and key.endswith(">"):
            inner = key[1:-1]
            self._root.bind(f"<KeyRelease-{inner}>", callback)
        else:
            self._root.bind(f"<KeyRelease-{key}>", callback)
