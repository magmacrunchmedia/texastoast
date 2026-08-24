from __future__ import annotations

from dataclasses import dataclass

from texastoast.render.abstract import as_ui_surface


@dataclass
class HUDStat:
    label: str
    value: float = 0
    max_value: float = 100
    color: str = "#e94560"
    show_bar: bool = True
    show_text: bool = True


class HUD:
    """Heads-up display overlay for score, health, etc.

    ``surface`` accepts a :class:`~texastoast.render.canvas.CanvasRenderer`
    (or any :class:`~texastoast.render.abstract.UISurface`) — in which case
    ``width``/``height`` default from it — or a bare ``tk.Canvas`` for
    backward compatibility.
    """

    def __init__(
        self,
        surface,
        width: int | None = None,
        height: int | None = None,
        font: tuple = ("Courier", 10),
        padding: int = 8,
    ):
        self._surface = as_ui_surface(surface, width, height)
        self._width = width if width is not None else self._surface.width
        self._height = height if height is not None else self._surface.height
        self._font = font
        self._padding = padding
        self._tag = "hud"
        self._stats: dict[str, HUDStat] = {}
        self._custom_texts: dict[str, tuple[str, float, float, dict]] = {}

    def add_stat(self, key: str, label: str, value: float = 100,
                 max_value: float = 100, color: str = "#e94560"):
        self._stats[key] = HUDStat(label=label, max_value=max_value, color=color)
        self.set_stat(key, value)

    def set_stat(self, key: str, value: float):
        """Set a stat, clamped to ``[0, max_value]``."""
        if key in self._stats:
            self._stats[key].value = max(0, min(value, self._stats[key].max_value))

    def add_text(self, key: str, text: str, x: float, y: float, **kwargs):
        defaults = {"fill": "#ffffff", "font": self._font, "anchor": "nw"}
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
        self._surface.clear_group(self._tag)

    def render(self):
        self._surface.begin_group(self._tag)
        self._render_stats()
        self._render_texts()

    def _render_stats(self):
        x = self._padding
        y = self._padding
        bar_width = 120
        bar_height = 10
        line_height = 20

        for stat in self._stats.values():
            if stat.show_text:
                self._surface.ui_text(
                    x, y, stat.label, fill="#cccccc",
                    font=self._font, anchor="nw",
                    group=self._tag,
                )
                value_text = f"{int(stat.value)}/{int(stat.max_value)}"
                self._surface.ui_text(
                    x + bar_width + 8, y, value_text, fill="#aaaaaa",
                    font=self._font, anchor="nw",
                    group=self._tag,
                )

            if stat.show_bar:
                bar_x = x
                bar_y = y + (14 if stat.show_text else 0)
                ratio = stat.value / stat.max_value if stat.max_value > 0 else 0
                self._surface.ui_rect(
                    bar_x, bar_y, bar_width, bar_height,
                    fill="#333333", outline="#555555", outline_width=1,
                    group=self._tag,
                )
                if ratio > 0:
                    self._surface.ui_rect(
                        bar_x, bar_y, bar_width * ratio, bar_height,
                        fill=stat.color,
                        group=self._tag,
                    )

            y += line_height + (bar_height + 4 if stat.show_bar else 0)

    def _render_texts(self):
        for text, x, y, opts in self._custom_texts.values():
            self._surface.ui_text(
                x, y, text,
                fill=opts.get("fill", "#ffffff"),
                font=opts.get("font", self._font),
                anchor=str(opts.get("anchor", "nw")),
                width=opts.get("width"),
                group=self._tag,
            )
