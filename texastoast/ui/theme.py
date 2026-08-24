"""Colors and fonts for the built-in UI widgets.

Before 0.5.0 the palette was frozen as string literals scattered across three
widget files; restyling a game meant passing every color kwarg to every
widget. A :class:`Theme` states it once::

    from dataclasses import replace
    from texastoast import DEFAULT_THEME, Theme

    ocean = Theme(primary="#4fc3f7", selection_fill="#112233")
    # or tweak the default:
    ocean = replace(DEFAULT_THEME, primary="#4fc3f7")

    dialogue = DialogueBox(renderer, theme=ocean)

Widgets resolve explicit style kwargs first, then the theme, so existing code
that passes ``selected_color=...`` keeps winning. :data:`DEFAULT_THEME`
carries exactly the pre-0.5.0 values — a game that never mentions themes
renders identically.

Layout metrics (menu width, bar sizes) are deliberately not here: those are
layout, not theme.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """The widget palette. Frozen: build variants with ``dataclasses.replace``.

    Widgets know their own font *sizes* (a speaker line is smaller than body
    text — that is role knowledge); the theme supplies the family via
    :meth:`font`.
    """

    primary: str = "#e94560"        # accents: speaker names, selection, stat bars
    text: str = "#ffffff"           # body text
    dim_text: str = "#aaaaaa"       # hints, secondary values
    label_text: str = "#cccccc"     # stat labels
    disabled: str = "#555555"       # unselectable menu items
    box_fill: str = "#000000"       # dialogue/menu panel fill
    box_outline: str = "#ffffff"    # panel border
    outline_width: int = 2          # panel border width
    selection_fill: str = "#331111" # selected menu row background
    bar_fill: str = "#333333"       # stat bar track
    bar_outline: str = "#555555"    # stat bar border
    font_family: str = "Courier"

    def font(self, size: int, *style: str) -> tuple:
        """A tk font tuple in this theme's family: ``theme.font(10, "bold")``."""
        return (self.font_family, size, *style)


DEFAULT_THEME = Theme()
