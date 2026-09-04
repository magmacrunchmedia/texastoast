"""UI widget tests.

The widgets draw onto the same canvas the renderer clears every frame, so the
thing worth pinning down is that a widget which believes it is showing puts its
items back on any render() — see test_dialogue_survives_a_canvas_clear.
"""
import pytest

# See test_render.py: skips a missing tkinter, where requires_tk skips a
# missing display. Both conditions have to be handled to collect on a Pi.
tk = pytest.importorskip("tkinter", reason="tkinter is not installed")

from conftest import requires_tk

from texastoast.ui import HUD, DialogueBox, Menu

pytestmark = requires_tk


@pytest.fixture
def canvas(tk_root):
    c = tk.Canvas(tk_root, width=400, height=300)
    c.pack()
    return c


# ── DialogueBox ─────────────────────────────────────────────────────

def test_dialogue_survives_a_canvas_clear(canvas):
    """The bug this suite exists for.

    CanvasRenderer.clear() wipes the whole canvas every frame. A dialogue that
    drew itself once from show() vanished but stayed active, so the game looked
    frozen behind an invisible modal.
    """
    dialogue = DialogueBox(canvas, 400, 300, speed=0.01)
    dialogue.show("Hello there", speaker="Wizard")
    dialogue.render()
    assert canvas.find_withtag("dialogue")

    canvas.delete("all")
    assert not canvas.find_withtag("dialogue")

    dialogue.render()
    assert canvas.find_withtag("dialogue")
    assert dialogue.active


def test_dialogue_types_out_over_time(canvas):
    dialogue = DialogueBox(canvas, 400, 300, speed=0.1)
    dialogue.show("abcde")
    assert dialogue.displayed == ""

    dialogue.update(0.1)
    assert dialogue.displayed == "a"
    dialogue.update(0.2)
    assert dialogue.displayed == "abc"
    assert not dialogue.waiting

    dialogue.update(1.0)
    assert dialogue.displayed == "abcde"
    assert dialogue.waiting


def test_dialogue_typing_is_frame_rate_independent(canvas):
    """Same elapsed time reveals the same text, whatever the frame rate."""
    revealed = []
    for fps in (30, 60, 240):
        dialogue = DialogueBox(canvas, 400, 300, speed=0.02)
        dialogue.show("the quick brown fox jumps")
        for _ in range(fps):
            dialogue.update(1.0 / fps)
        revealed.append(dialogue.displayed)
    assert len(set(revealed)) == 1


def test_dialogue_dismiss_completes_then_closes(canvas):
    done = []
    dialogue = DialogueBox(canvas, 400, 300, speed=0.1)
    dialogue.show("abcde", on_complete=lambda: done.append(True))
    dialogue.update(0.1)

    # First dismiss skips to the end rather than closing.
    dialogue.dismiss()
    assert dialogue.displayed == "abcde"
    assert dialogue.active
    assert not done

    # Second dismiss closes and fires the callback.
    dialogue.dismiss()
    assert not dialogue.active
    assert done == [True]

    dialogue.render()
    assert not canvas.find_withtag("dialogue")


def test_dialogue_with_empty_text_is_immediately_dismissable(canvas):
    done = []
    dialogue = DialogueBox(canvas, 400, 300)
    dialogue.show("", on_complete=lambda: done.append(True))
    assert dialogue.waiting
    dialogue.dismiss()
    assert not dialogue.active
    assert done == [True]


def test_dialogue_update_is_inert_when_inactive(canvas):
    dialogue = DialogueBox(canvas, 400, 300, speed=0.01)
    dialogue.update(1.0)  # no show() yet
    assert dialogue.displayed == ""
    assert not dialogue.active


# ── Menu ────────────────────────────────────────────────────────────

def test_menu_survives_a_canvas_clear(canvas):
    menu = Menu(canvas, 400, 300)
    menu.show(["Resume", "Quit"], title="PAUSED")
    menu.render()
    assert canvas.find_withtag("menu")

    canvas.delete("all")
    menu.render()
    assert canvas.find_withtag("menu")
    assert menu.active


def test_menu_render_is_a_no_op_when_hidden(canvas):
    menu = Menu(canvas, 400, 300)
    menu.render()
    assert not canvas.find_withtag("menu")

    menu.show(["One", "Two"])
    menu.render()
    assert canvas.find_withtag("menu")

    menu.hide()
    menu.render()
    assert not canvas.find_withtag("menu")


def test_menu_navigation_skips_disabled_items(canvas):
    menu = Menu(canvas, 400, 300)
    menu.show(["One", "Two", "Three"])
    menu.set_enabled(1, False)

    menu.move_down()
    assert menu.selected_index == 2
    menu.move_up()
    assert menu.selected_index == 0


def test_menu_navigation_stops_at_the_ends(canvas):
    menu = Menu(canvas, 400, 300)
    menu.show(["One", "Two"])
    menu.move_up()
    assert menu.selected_index == 0
    menu.move_down()
    menu.move_down()
    assert menu.selected_index == 1


def test_menu_confirm_hides_and_reports_the_selection(canvas):
    picked = []
    menu = Menu(canvas, 400, 300)
    menu.show(["One", "Two"], on_select=lambda i, label: picked.append((i, label)))
    menu.move_down()
    menu.confirm()
    assert picked == [(1, "Two")]
    assert not menu.active


def test_menu_confirm_ignores_a_disabled_selection(canvas):
    picked = []
    menu = Menu(canvas, 400, 300)
    menu.show(["One", "Two"], on_select=lambda i, label: picked.append(label))
    # Disabling the selection snaps off it, so force the state directly.
    menu._items[0]["enabled"] = False
    menu.confirm()
    assert picked == []
    assert menu.active


def test_menu_show_ignores_an_empty_item_list(canvas):
    menu = Menu(canvas, 400, 300)
    menu.show([])
    assert not menu.active


# ── HUD ─────────────────────────────────────────────────────────────

def test_hud_clamps_stats_on_add_and_set(canvas):
    hud = HUD(canvas, 400, 300)
    hud.add_stat("hp", "HP", value=500, max_value=100)
    assert hud._stats["hp"].value == 100

    hud.set_stat("hp", -20)
    assert hud._stats["hp"].value == 0


def test_hud_renders_and_clears(canvas):
    hud = HUD(canvas, 400, 300)
    hud.add_stat("hp", "HP", value=50, max_value=100)
    hud.add_text("score", "Score: 0", 10, 10)
    hud.render()
    assert canvas.find_withtag("hud")

    hud.clear()
    assert not canvas.find_withtag("hud")


def test_hud_set_text_keeps_position_and_options(canvas):
    hud = HUD(canvas, 400, 300)
    hud.add_text("score", "Score: 0", 12, 34, fill="#fdd835")
    hud.set_text("score", "Score: 99")
    text, x, y, opts = hud._custom_texts["score"]
    assert (text, x, y) == ("Score: 99", 12, 34)
    assert opts["fill"] == "#fdd835"
