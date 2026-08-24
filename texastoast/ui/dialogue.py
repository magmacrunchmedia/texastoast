from __future__ import annotations

import tkinter as tk
from typing import Optional, Callable


class DialogueBox:
    """Canvas-based dialogue box with typewriter text and portrait support."""

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
        self._displayed = ""
        self._char_index = 0
        self._after_id: Optional[str] = None
        self._on_complete: Optional[Callable] = None
        self._speaker = ""
        self._waiting = False
        self._tag = "dialogue"

    @property
    def active(self) -> bool:
        return self._active

    @property
    def waiting(self) -> bool:
        return self._waiting

    def show(self, text: str, speaker: str = "", on_complete: Optional[Callable] = None):
        self._full_text = text
        self._speaker = speaker
        self._on_complete = on_complete
        self._displayed = ""
        self._char_index = 0
        self._active = True
        self._waiting = False
        self._draw_box()
        self._tick_type()

    def dismiss(self):
        if not self._active:
            return
        if self._waiting:
            self._active = False
            self._clear()
            if self._on_complete:
                self._on_complete()
        elif not self._waiting and self._char_index < len(self._full_text):
            self._displayed = self._full_text
            self._char_index = len(self._full_text)
            self._render_text()
            self._waiting = True

    def _tick_type(self):
        if not self._active:
            return
        if self._char_index < len(self._full_text):
            self._displayed += self._full_text[self._char_index]
            self._char_index += 1
            self._render_text()
            self._after_id = self._canvas.after(
                int(self._speed * 1000), self._tick_type
            )
        else:
            self._waiting = True

    def _draw_box(self):
        self._clear()
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

    def _render_text(self):
        self._canvas.delete(f"{self._tag}_text")
        x1 = self._padding
        y1 = self._height - self._box_height - self._padding

        text_x = x1 + self._padding
        text_y = y1 + (self._padding + 14 if not self._speaker else self._padding + 28)

        self._canvas.create_text(
            text_x, text_y,
            text=self._displayed, fill="#ffffff",
            font=self._font, anchor=tk.NW,
            width=self._width - self._padding * 4,
            tags=(self._tag, f"{self._tag}_text"),
        )

        if self._waiting:
            prompt = "[A] continue"
            self._canvas.create_text(
                self._width - self._padding * 2,
                self._height - self._padding * 2,
                text=prompt, fill="#aaaaaa",
                font=("Courier", 9), anchor=tk.SE,
                tags=(self._tag, f"{self._tag}_text"),
            )

    def _clear(self):
        if self._after_id:
            self._canvas.after_cancel(self._after_id)
            self._after_id = None
        self._canvas.delete(self._tag)
