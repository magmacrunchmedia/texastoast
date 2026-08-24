from __future__ import annotations

from collections.abc import Callable

from texastoast.render.abstract import as_ui_surface
from texastoast.ui.theme import DEFAULT_THEME, Theme


class DialogueBox:
    """Dialogue box with typewriter text and portrait support.

    Drawing is frame-driven, like :class:`~texastoast.ui.hud.HUD`: call
    :meth:`update` from the game's update function and :meth:`render` from its
    render function. A renderer that clears the canvas each frame would
    otherwise wipe the box off screen while the box still believes it is up.

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
        box_height: int = 100,
        padding: int = 12,
        font: tuple | None = None,
        speed: float = 0.03,
        theme: Theme | None = None,
    ):
        self._surface = as_ui_surface(surface, width, height)
        self._width = width if width is not None else self._surface.width
        self._height = height if height is not None else self._surface.height
        self._box_height = box_height
        self._padding = padding
        self._theme = theme or DEFAULT_THEME
        # An explicit font still wins; the theme supplies the default.
        self._font = font or self._theme.font(12)
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
        self._surface.begin_group(self._tag)
        if not self._active:
            return

        x1 = self._padding
        y1 = self._height - self._box_height - self._padding
        x2 = self._width - self._padding
        y2 = self._height - self._padding

        theme = self._theme
        self._surface.ui_rect(
            x1, y1, x2 - x1, y2 - y1,
            fill=theme.box_fill, outline=theme.box_outline,
            outline_width=theme.outline_width,
            group=self._tag,
        )

        if self._speaker:
            self._surface.ui_text(
                x1 + self._padding, y1 + 4,
                self._speaker, fill=theme.primary,
                font=theme.font(10, "bold"), anchor="nw",
                group=self._tag,
            )

        text_x = x1 + self._padding
        text_y = y1 + (self._padding + 28 if self._speaker else self._padding + 14)

        self._surface.ui_text(
            text_x, text_y,
            self.displayed, fill=theme.text,
            font=self._font, anchor="nw",
            width=self._width - self._padding * 4,
            group=self._tag,
        )

        if self._waiting:
            self._surface.ui_text(
                self._width - self._padding * 2,
                self._height - self._padding * 2,
                "[A] continue", fill=theme.dim_text,
                font=theme.font(9), anchor="se",
                group=self._tag,
            )

    def _clear(self):
        self._surface.clear_group(self._tag)
