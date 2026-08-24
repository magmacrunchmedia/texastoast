"""Theme tests.

The load-bearing test is the pinned-defaults one: DEFAULT_THEME must carry
exactly the values that were hardcoded in the widgets before 0.5.0, so a game
that never mentions themes renders pixel-identically across the upgrade.
"""
import dataclasses

import pytest

from texastoast.ui import DEFAULT_THEME, HUD, DialogueBox, Menu, Theme


def test_default_theme_values_pinned():
    # Each value below was a string literal in the widget files before 0.5.0.
    # Changing any of them silently restyles every default-themed game.
    assert DEFAULT_THEME.primary == "#e94560"
    assert DEFAULT_THEME.text == "#ffffff"
    assert DEFAULT_THEME.dim_text == "#aaaaaa"
    assert DEFAULT_THEME.label_text == "#cccccc"
    assert DEFAULT_THEME.disabled == "#555555"
    assert DEFAULT_THEME.box_fill == "#000000"
    assert DEFAULT_THEME.box_outline == "#ffffff"
    assert DEFAULT_THEME.outline_width == 2
    assert DEFAULT_THEME.selection_fill == "#331111"
    assert DEFAULT_THEME.bar_fill == "#333333"
    assert DEFAULT_THEME.bar_outline == "#555555"
    assert DEFAULT_THEME.font_family == "Courier"


def test_theme_is_frozen():
    # DEFAULT_THEME is a shared module singleton; freezing makes accidental
    # cross-game mutation impossible.
    with pytest.raises(dataclasses.FrozenInstanceError):
        DEFAULT_THEME.primary = "#123456"


def test_replace_builds_a_variant():
    ocean = dataclasses.replace(DEFAULT_THEME, primary="#4fc3f7")
    assert ocean.primary == "#4fc3f7"
    assert ocean.text == DEFAULT_THEME.text
    assert DEFAULT_THEME.primary == "#e94560"  # the original is untouched


def test_font_helper():
    assert DEFAULT_THEME.font(12) == ("Courier", 12)
    assert DEFAULT_THEME.font(10, "bold") == ("Courier", 10, "bold")
    assert Theme(font_family="Terminal").font(9) == ("Terminal", 9)


# ── Widgets consume the theme (via a fake surface, no display) ──────


class FakeSurface:
    width, height = 640, 480

    def __init__(self):
        self.groups = {}

    def begin_group(self, group):
        self.groups[group] = []

    def clear_group(self, group):
        self.groups.pop(group, None)

    def ui_rect(self, x, y, w, h, *, fill, outline="", outline_width=0, group=""):
        self.groups.setdefault(group, []).append(("rect", fill, outline))

    def ui_text(self, x, y, text, *, fill, font=None, anchor="nw",
                width=None, group=""):
        self.groups.setdefault(group, []).append(("text", text, fill, font))


CUSTOM = Theme(primary="#4fc3f7", text="#001122", box_fill="#222222",
               selection_fill="#003344", font_family="Terminal")


def test_dialogue_uses_custom_theme():
    surface = FakeSurface()
    dialogue = DialogueBox(surface, theme=CUSTOM, speed=0)
    dialogue.show("Hi", speaker="Wizard")
    dialogue.update(0.1)
    dialogue.render()

    items = surface.groups["dialogue"]
    rects = [c for c in items if c[0] == "rect"]
    assert rects[0][1] == "#222222"                    # box_fill
    speaker = next(c for c in items if c[0] == "text" and c[1] == "Wizard")
    assert speaker[2] == "#4fc3f7"                     # primary
    assert speaker[3] == ("Terminal", 10, "bold")      # theme font family
    body = next(c for c in items if c[0] == "text" and c[1] == "Hi")
    assert body[2] == "#001122"                        # text


def test_menu_uses_custom_theme():
    surface = FakeSurface()
    menu = Menu(surface, theme=CUSTOM)
    menu.show(["One", "Two"])
    menu.render()

    items = surface.groups["menu"]
    fills = [c[1] for c in items if c[0] == "rect"]
    assert "#222222" in fills                          # box_fill
    assert "#003344" in fills                          # selection_fill
    selected = next(c for c in items if c[0] == "text" and c[1] == "> One")
    assert selected[2] == "#4fc3f7"                    # primary as selected


def test_hud_uses_custom_theme():
    surface = FakeSurface()
    hud = HUD(surface, theme=CUSTOM)
    hud.add_stat("hp", "HP", value=50, max_value=100)
    hud.render()

    items = surface.groups["hud"]
    filled = [c for c in items if c[0] == "rect"][1]
    assert filled[1] == "#4fc3f7"                      # stat bar from primary


def test_explicit_kwargs_beat_theme():
    surface = FakeSurface()
    menu = Menu(surface, selected_color="#00ff00", theme=CUSTOM)
    menu.show(["One"])
    menu.render()
    selected = next(c for c in surface.groups["menu"]
                    if c[0] == "text" and c[1] == "> One")
    assert selected[2] == "#00ff00"


def test_hud_add_stat_color_beats_theme():
    surface = FakeSurface()
    hud = HUD(surface, theme=CUSTOM)
    hud.add_stat("xp", "XP", value=100, max_value=100, color="#fdd835")
    hud.render()
    filled = [c for c in surface.groups["hud"] if c[0] == "rect"][1]
    assert filled[1] == "#fdd835"
