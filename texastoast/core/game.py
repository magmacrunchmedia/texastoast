from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

from texastoast.core.config import Config, DEFAULT_CONFIG
from texastoast.core.loop import GameLoop


class Game:
    """Main game class. Manages the tkinter window and game lifecycle."""

    def __init__(
        self,
        title: str = DEFAULT_CONFIG.title,
        width: int = DEFAULT_CONFIG.width,
        height: int = DEFAULT_CONFIG.height,
        fps: int = DEFAULT_CONFIG.fps,
        config: Optional[Config] = None,
    ):
        self.config = config or Config(title=title, width=width, height=height, fps=fps)
        self._root = tk.Tk()
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

        self._loop: Optional[GameLoop] = None
        self._update_fn: Optional[Callable[[float], None]] = None
        self._render_fn: Optional[Callable[[], None]] = None

    @property
    def root(self) -> tk.Tk:
        return self._root

    @property
    def loop(self) -> Optional[GameLoop]:
        return self._loop

    def set_update(self, fn: Callable[[float], None]):
        self._update_fn = fn

    def set_render(self, fn: Callable[[], None]):
        self._render_fn = fn

    def start(self):
        update = self._update_fn or (lambda dt: None)
        render = self._render_fn or (lambda: None)
        self._loop = GameLoop(self._root, update, render, self.config.fps)
        self._loop.start()
        self._root.mainloop()

    def quit(self):
        if self._loop:
            self._loop.stop()
        self._root.quit()
        self._root.destroy()

    def bind_key(self, key: str, callback: Callable):
        self._root.bind(key, callback)

    def bind_key_release(self, key: str, callback: Callable):
        self._root.bind(key, callback)
