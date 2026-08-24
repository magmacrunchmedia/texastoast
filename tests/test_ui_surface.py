"""UI widgets against a fake UISurface — no display needed.

The 0.4.0 seam: widgets draw through the UISurface protocol, so their logic
is testable headlessly. The tkinter-specific behaviour (tag composition over
a real canvas) stays covered in test_ui.py.
"""
from texastoast.ui import HUD, DialogueBox, Menu


class FakeUISurface:
    """Records draw calls; the group model of a retained-mode backend."""

    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.calls: list[tuple] = []
        self.groups: dict[str, list[tuple]] = {}

    def begin_group(self, group):
        self.calls.append(("begin_group", group))
        self.groups[group] = []

    def clear_group(self, group):
        self.calls.append(("clear_group", group))
        self.groups.pop(group, None)

    def ui_rect(self, x, y, w, h, *, fill, outline="", outline_width=0, group=""):
        item = ("rect", x, y, w, h, fill)
        self.calls.append(item)
        self.groups.setdefault(group, []).append(item)

    def ui_text(self, x, y, text, *, fill, font=None, anchor="nw",
                width=None, group=""):
        item = ("text", x, y, text, fill, anchor)
        self.calls.append(item)
        self.groups.setdefault(group, []).append(item)


def test_widgets_default_dimensions_from_the_surface():
    surface = FakeUISurface(width=320, height=240)
    dialogue = DialogueBox(surface)
    menu = Menu(surface)
    hud = HUD(surface)
    assert dialogue._width == 320 and dialogue._height == 240
    assert menu._width == 320 and menu._height == 240
    assert hud._width == 320 and hud._height == 240


def test_explicit_dimensions_still_win():
    surface = FakeUISurface(width=320, height=240)
    dialogue = DialogueBox(surface, width=640, height=480)
    assert dialogue._width == 640
    assert dialogue._height == 480


def test_dialogue_draws_into_its_group():
    surface = FakeUISurface()
    dialogue = DialogueBox(surface, speed=0)
    dialogue.show("Hello", speaker="Wizard")
    dialogue.update(0.1)
    dialogue.render()

    assert surface.groups["dialogue"], "dialogue drew nothing"
    texts = [c for c in surface.groups["dialogue"] if c[0] == "text"]
    assert any("Hello" in c[3] for c in texts)
    assert any("Wizard" in c[3] for c in texts)


def test_inactive_dialogue_renders_nothing_but_clears_its_frame():
    surface = FakeUISurface()
    dialogue = DialogueBox(surface)
    dialogue.render()
    assert surface.calls == [("begin_group", "dialogue")]
    assert surface.groups["dialogue"] == []


def test_menu_marks_the_selection():
    surface = FakeUISurface()
    menu = Menu(surface)
    menu.show(["Resume", "Quit"], title="PAUSED")
    menu.move_down()
    menu.render()

    texts = [c for c in surface.groups["menu"] if c[0] == "text"]
    assert any(c[3] == "> Quit" for c in texts)
    assert any(c[3] == "  Resume" for c in texts)
    assert any(c[3] == "PAUSED" for c in texts)


def test_menu_hide_clears_its_group():
    surface = FakeUISurface()
    menu = Menu(surface)
    menu.show(["One"])
    menu.render()
    assert surface.groups.get("menu")
    menu.hide()
    assert "menu" not in surface.groups


def test_hud_draws_stat_bars_and_texts():
    surface = FakeUISurface()
    hud = HUD(surface)
    hud.add_stat("hp", "HP", value=50, max_value=100)
    hud.add_text("score", "Score: 3", 10, 10)
    hud.render()

    items = surface.groups["hud"]
    rects = [c for c in items if c[0] == "rect"]
    texts = [c for c in items if c[0] == "text"]
    # Background bar plus the filled half.
    assert len(rects) == 2
    assert rects[1][3] == rects[0][3] / 2  # 50/100 → half width
    assert any(c[3] == "HP" for c in texts)
    assert any(c[3] == "50/100" for c in texts)
    assert any(c[3] == "Score: 3" for c in texts)
