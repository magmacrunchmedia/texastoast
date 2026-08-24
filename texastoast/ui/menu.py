from __future__ import annotations

import tkinter as tk
from typing import Optional, Callable


class Menu:
    """Canvas-based selectable menu with keyboard/controller navigation."""

    def __init__(
        self,
        canvas: tk.Canvas,
        width: int = 640,
        height: int = 480,
        font: tuple = ("Courier", 14),
        selected_color: str = "#e94560",
        normal_color: str = "#ffffff",
        disabled_color: str = "#555555",
        item_padding: int = 8,
    ):
        self._canvas = canvas
        self._width = width
        self._height = height
        self._font = font
        self._selected_color = selected_color
        self._normal_color = normal_color
        self._disabled_color = disabled_color
        self._item_padding = item_padding

        self._active = False
        self._items: list[dict] = []
        self._selected = 0
        self._on_select: Optional[Callable[[int, str], None]] = None
        self._on_cancel: Optional[Callable] = None
        self._tag = "menu"
        self._title = ""

    @property
    def active(self) -> bool:
        return self._active

    @property
    def selected_index(self) -> int:
        return self._selected

    def show(
        self,
        items: list[str],
        on_select: Optional[Callable[[int, str], None]] = None,
        on_cancel: Optional[Callable] = None,
        title: str = "",
        selected: int = 0,
    ):
        if not items:
            return
        self._items = [{"label": label, "enabled": True} for label in items]
        self._selected = max(0, min(selected, len(self._items) - 1))
        self._snap_to_enabled()
        self._on_select = on_select
        self._on_cancel = on_cancel
        self._title = title
        self._active = True
        self._draw()

    def hide(self):
        self._active = False
        self._canvas.delete(self._tag)

    def move_up(self):
        if not self._active or not self._items:
            return
        new = self._selected
        while new > 0:
            new -= 1
            if self._items[new]["enabled"]:
                self._selected = new
                self._draw()
                return

    def move_down(self):
        if not self._active or not self._items:
            return
        new = self._selected
        while new < len(self._items) - 1:
            new += 1
            if self._items[new]["enabled"]:
                self._selected = new
                self._draw()
                return

    def confirm(self):
        if not self._active or not self._items:
            return
        item = self._items[self._selected]
        if not item["enabled"]:
            return
        self.hide()
        if self._on_select:
            self._on_select(self._selected, item["label"])

    def cancel(self):
        if not self._active:
            return
        self.hide()
        if self._on_cancel:
            self._on_cancel()

    def set_enabled(self, index: int, enabled: bool):
        if 0 <= index < len(self._items):
            self._items[index]["enabled"] = enabled
            if self._active:
                self._snap_to_enabled()
                self._draw()

    def _snap_to_enabled(self):
        if not self._items:
            return
        if self._items[self._selected]["enabled"]:
            return
        for i in range(len(self._items)):
            if self._items[i]["enabled"]:
                self._selected = i
                return

    def _draw(self):
        self._canvas.delete(self._tag)

        menu_width = 280
        item_height = 32
        total_h = len(self._items) * item_height + self._item_padding * 2
        if self._title:
            total_h += 28

        cx = self._width / 2
        cy = self._height / 2
        x1 = cx - menu_width / 2
        y1 = cy - total_h / 2
        x2 = cx + menu_width / 2
        y2 = cy + total_h / 2

        self._canvas.create_rectangle(x1 - 4, y1 - 4, x2 + 4, y2 + 4,
                                      fill="#000000", outline="#ffffff",
                                      width=2, tags=self._tag)

        y = y1 + self._item_padding

        if self._title:
            self._canvas.create_text(
                cx, y + 10, text=self._title,
                fill=self._normal_color, font=("Courier", 11, "bold"),
                tags=self._tag,
            )
            y += 28

        for i, item in enumerate(self._items):
            is_selected = (i == self._selected)
            is_enabled = item["enabled"]

            if is_selected and is_enabled:
                self._canvas.create_rectangle(
                    x1 + 4, y, x2 - 4, y + item_height,
                    fill="#331111", outline="",
                    tags=self._tag,
                )
                color = self._selected_color
                prefix = "> "
            else:
                color = self._normal_color if is_enabled else self._disabled_color
                prefix = "  "

            self._canvas.create_text(
                x1 + self._item_padding + 8, y + item_height / 2,
                text=prefix + item["label"], fill=color,
                font=self._font, anchor=tk.W,
                tags=self._tag,
            )
            y += item_height
