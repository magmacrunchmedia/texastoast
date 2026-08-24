from __future__ import annotations

import tkinter as tk
from collections.abc import Callable


class DialogueBox:
    """Canvas-based dialogue box with typewriter text and portrait support.

    Drawing is frame-driven, like :class:`~texastoast.ui.hud.HUD`: call
    :meth:`update` from the game's update function and :meth:`render` from its
    render function. A renderer that clears the canvas each frame would
    otherwise wipe the box off screen while the box still believes it is up.
    """

    def __init__(
        self,
        canvas: tk.Canvas,
        width: int = 640,
        height: int = 480,
        box_height: int = 100,
        padding: int = 12,
        font: tuple = ("Courier", 12),
        speed: float = 0.03,
    ):
        self._canvas = canvas
        self._width = width
        self._height = height
        self._box_height = box_height
        self._padding = padding
        self._font = font
        self._speed = speed

        self._active = False
        self._full_text = ""
        self._char_index = 0
        self._elapsed = 0.0
        self._on_complete: Callable | None = None
        self._speaker = ""
        self._waiting = False
        self._tag = "dialogue"

    @property
    def active(self) -> bool:
        return self._active

    @property
    def waiting(self) -> bool:
        """True once the full text is on screen and a dismiss will close it."""
        return self._waiting

    @property
    def displayed(self) -> str:
        return self._full_text[:self._char_index]

    def show(self, text: str, speaker: str = "", on_complete: Callable | None = None):
        self._full_text = text
        self._speaker = speaker
        self._on_complete = on_complete
        self._char_index = 0
        self._elapsed = 0.0
        self._active = True
        # Empty text has nothing to type, so it is immediately dismissable.
        self._waiting = not text

    def update(self, dt: float):
        """Advance the typewriter by ``dt`` seconds."""
        if not self._active or self._waiting:
            return

        if self._speed <= 0:
            self._char_index = len(self._full_text)
        else:
            self._elapsed += dt
            revealed = int(self._elapsed / self._speed)
            if revealed > self._char_index:
                self._char_index = min(revealed, len(self._full_text))

        if self._char_index >= len(self._full_text):
            self._waiting = True

    def dismiss(self):
        """Skip to the end of the text, or close the box if it is already there."""
        if not self._active:
            return
        if self._waiting:
            self._active = False
            self._clear()
            if self._on_complete:
                self._on_complete()
        else:
            self._char_index = len(self._full_text)
            self._waiting = True

    def render(self):
        """Draw the box. Safe to call every frame, active or not."""
        self._canvas.delete(self._tag)
        if not self._active:
            return

        x1 = self._padding
        y1 = self._height - self._box_height - self._padding
        x2 = self._width - self._padding
        y2 = self._height - self._padding

        self._canvas.create_rectangle(x1, y1, x2, y2,
                                      fill="#000000", outline="#ffffff",
                                      width=2, tags=self._tag)

        if self._speaker:
            self._canvas.create_text(
                x1 + self._padding, y1 + 4,
                text=self._speaker, fill="#e94560",
                font=("Courier", 10, "bold"), anchor=tk.NW,
                tags=self._tag,
            )

        text_x = x1 + self._padding
        text_y = y1 + (self._padding + 28 if self._speaker else self._padding + 14)

        self._canvas.create_text(
            text_x, text_y,
            text=self.displayed, fill="#ffffff",
            font=self._font, anchor=tk.NW,
            width=self._width - self._padding * 4,
            tags=self._tag,
        )

        if self._waiting:
            self._canvas.create_text(
                self._width - self._padding * 2,
                self._height - self._padding * 2,
                text="[A] continue", fill="#aaaaaa",
                font=("Courier", 9), anchor=tk.SE,
                tags=self._tag,
            )

    def _clear(self):
        self._canvas.delete(self._tag)
