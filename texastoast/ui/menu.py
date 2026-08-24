from __future__ import annotations

from collections.abc import Callable

from texastoast.render.abstract import as_ui_surface
from texastoast.ui.theme import DEFAULT_THEME, Theme


class Menu:
    """Selectable menu with keyboard/controller navigation.

    Drawing is frame-driven, like :class:`~texastoast.ui.hud.HUD`: call
    :meth:`render` from the game's render function. A renderer that clears the
    canvas each frame would otherwise wipe the menu off screen while the menu
    still believes it is up.

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
        font: tuple | None = None,
        selected_color: str | None = None,
        normal_color: str | None = None,
        disabled_color: str | None = None,
        item_padding: int = 8,
        theme: Theme | None = None,
    ):
        self._surface = as_ui_surface(surface, width, height)
        self._width = width if width is not None else self._surface.width
        self._height = height if height is not None else self._surface.height
        self._theme = theme or DEFAULT_THEME
        # Explicit style kwargs still win; the theme supplies the defaults.
        self._font = font or self._theme.font(14)
        self._selected_color = selected_color or self._theme.primary
        self._normal_color = normal_color or self._theme.text
        self._disabled_color = disabled_color or self._theme.disabled
        self._item_padding = item_padding

        self._active = False
        self._items: list[dict] = []
        self._selected = 0
        self._on_select: Callable[[int, str], None] | None = None
        self._on_cancel: Callable | None = None
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
        on_select: Callable[[int, str], None] | None = None,
        on_cancel: Callable | None = None,
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

    def hide(self):
        self._active = False
        self._surface.clear_group(self._tag)

    def move_up(self):
        if not self._active or not self._items:
            return
        new = self._selected
        while new > 0:
            new -= 1
            if self._items[new]["enabled"]:
                self._selected = new
                return

    def move_down(self):
        if not self._active or not self._items:
            return
        new = self._selected
        while new < len(self._items) - 1:
            new += 1
            if self._items[new]["enabled"]:
                self._selected = new
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

    def _snap_to_enabled(self):
        if not self._items:
            return
        if self._items[self._selected]["enabled"]:
            return
        for i in range(len(self._items)):
            if self._items[i]["enabled"]:
                self._selected = i
                return

    def render(self):
        """Draw the menu. Safe to call every frame, active or not."""
        self._surface.begin_group(self._tag)
        if not self._active:
            return

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

        theme = self._theme
        self._surface.ui_rect(
            x1 - 4, y1 - 4, (x2 + 4) - (x1 - 4), (y2 + 4) - (y1 - 4),
            fill=theme.box_fill, outline=theme.box_outline,
            outline_width=theme.outline_width,
            group=self._tag,
        )

        y = y1 + self._item_padding

        if self._title:
            self._surface.ui_text(
                cx, y + 10, self._title,
                fill=self._normal_color, font=theme.font(11, "bold"),
                anchor="center",
                group=self._tag,
            )
            y += 28

        for i, item in enumerate(self._items):
            is_selected = (i == self._selected)
            is_enabled = item["enabled"]

            if is_selected and is_enabled:
                self._surface.ui_rect(
                    x1 + 4, y, (x2 - 4) - (x1 + 4), item_height,
                    fill=theme.selection_fill,
                    group=self._tag,
                )
                color = self._selected_color
                prefix = "> "
            else:
                color = self._normal_color if is_enabled else self._disabled_color
                prefix = "  "

            self._surface.ui_text(
                x1 + self._item_padding + 8, y + item_height / 2,
                prefix + item["label"], fill=color,
                font=self._font, anchor="w",
                group=self._tag,
            )
            y += item_height
