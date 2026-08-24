from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HUDStat:
    label: str
    value: float = 0
    max_value: float = 100
    color: str = "#e94560"
    show_bar: bool = True
    show_text: bool = True


class HUD:
    """Canvas-based heads-up display overlay for score, health, etc."""

    def __init__(
        self,
        canvas: tk.Canvas,
        width: int = 640,
        height: int = 480,
        font: tuple = ("Courier", 10),
        padding: int = 8,
    ):
        self._canvas = canvas
        self._width = width
        self._height = height
        self._font = font
        self._padding = padding
        self._tag = "hud"
        self._stats: dict[str, HUDStat] = {}
        self._custom_texts: dict[str, tuple[str, float, float, dict]] = {}

    def add_stat(self, key: str, label: str, value: float = 100,
                 max_value: float = 100, color: str = "#e94560"):
        self._stats[key] = HUDStat(label=label, value=value,
                                   max_value=max_value, color=color)

    def set_stat(self, key: str, value: float):
        if key in self._stats:
            self._stats[key].value = max(0, min(value, self._stats[key].max_value))

    def add_text(self, key: str, text: str, x: float, y: float, **kwargs):
        defaults = {"fill": "#ffffff", "font": self._font, "anchor": tk.NW}
        defaults.update(kwargs)
        self._custom_texts[key] = (text, x, y, defaults)

    def remove_text(self, key: str):
        self._custom_texts.pop(key, None)

    def set_text(self, key: str, text: str):
        if key in self._custom_texts:
            old = self._custom_texts[key]
            self._custom_texts[key] = (text, old[1], old[2], old[3])

    def clear(self):
        self._stats.clear()
        self._custom_texts.clear()
        self._canvas.delete(self._tag)

    def render(self):
        self._canvas.delete(self._tag)
        self._render_stats()
        self._render_texts()

    def _render_stats(self):
        x = self._padding
        y = self._padding
        bar_width = 120
        bar_height = 10
        line_height = 20

        for key, stat in self._stats.items():
            if stat.show_text:
                self._canvas.create_text(
                    x, y, text=stat.label, fill="#cccccc",
                    font=self._font, anchor=tk.NW,
                    tags=self._tag,
                )
                value_text = f"{int(stat.value)}/{int(stat.max_value)}"
                self._canvas.create_text(
                    x + bar_width + 8, y, text=value_text, fill="#aaaaaa",
                    font=self._font, anchor=tk.NW,
                    tags=self._tag,
                )

            if stat.show_bar:
                bar_x = x
                bar_y = y + (14 if stat.show_text else 0)
                ratio = stat.value / stat.max_value if stat.max_value > 0 else 0
                self._canvas.create_rectangle(
                    bar_x, bar_y, bar_x + bar_width, bar_y + bar_height,
                    fill="#333333", outline="#555555",
                    tags=self._tag,
                )
                if ratio > 0:
                    self._canvas.create_rectangle(
                        bar_x, bar_y, bar_x + bar_width * ratio, bar_y + bar_height,
                        fill=stat.color, outline="",
                        tags=self._tag,
                    )

            y += line_height + (bar_height + 4 if stat.show_bar else 0)

    def _render_texts(self):
        for key, (text, x, y, opts) in self._custom_texts.items():
            self._canvas.create_text(x, y, text=text, tags=self._tag, **opts)
