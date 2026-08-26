"""CellBuffer — the framework-free half of every terminal backend.

Nothing here imports a terminal library, which is the point: these assertions
hold for the Textual backend today and for a hand-written ANSI one later, and
they run on a machine with neither installed.
"""

from texastoast.render.cellbuffer import EMPTY_CELL, Cell, CellBuffer


def test_starts_blank():
    buf = CellBuffer(4, 3)
    assert buf.width == 4
    assert buf.height == 3
    assert all(buf.get(x, y).is_blank for x in range(4) for y in range(3))
    assert buf.to_text() == "\n\n"


def test_write_and_read_back():
    buf = CellBuffer(10, 2)
    buf.write(2, 1, "hi", fg="#ff0000")
    assert buf.get(2, 1) == Cell("h", "#ff0000", None)
    assert buf.get(3, 1).char == "i"
    assert buf.to_text() == "\n  hi"


def test_write_clips_at_the_right_edge_without_wrapping():
    # Wrapping would silently corrupt the row below, which is worse than
    # truncating: a long HUD string is a normal occurrence, not a bug.
    buf = CellBuffer(4, 2)
    buf.write(2, 0, "abcdef")
    assert buf.to_text() == "  ab\n"


def test_write_clips_negative_coordinates():
    buf = CellBuffer(4, 1)
    buf.write(-2, 0, "abcd")
    assert buf.to_text() == "cd"


def test_write_past_the_bottom_is_dropped():
    buf = CellBuffer(4, 1)
    buf.write(0, 5, "nope")
    assert buf.to_text() == ""


def test_multiline_write_keeps_its_left_margin():
    buf = CellBuffer(6, 3)
    buf.write(2, 0, "ab\ncd")
    assert buf.to_text() == "  ab\n  cd\n"


def test_fill_paints_background_only_by_default():
    buf = CellBuffer(5, 3)
    buf.fill(1, 1, 3, 2, bg="#123456")
    assert buf.get(1, 1) == Cell(" ", None, "#123456")
    assert buf.get(0, 1).is_blank
    # Background-only means the text layer is untouched.
    assert buf.to_text() == "\n\n"


def test_fill_clips_to_the_buffer():
    buf = CellBuffer(3, 3)
    buf.fill(-2, -2, 10, 10, bg="#fff", char="#")
    assert buf.to_text() == "###\n###\n###"


def test_fill_with_zero_or_negative_size_is_a_no_op():
    buf = CellBuffer(3, 3)
    buf.fill(0, 0, 0, 5, bg="#fff", char="#")
    buf.fill(0, 0, 5, -1, bg="#fff", char="#")
    assert buf.to_text() == "\n\n"


def test_outline_strokes_only_the_border():
    buf = CellBuffer(4, 4)
    buf.outline(0, 0, 4, 4, color="#fff", char="#")
    assert buf.to_text() == "####\n#  #\n#  #\n####"


def test_clear_blanks_everything():
    buf = CellBuffer(4, 2)
    buf.write(0, 0, "abcd")
    buf.clear()
    assert buf.to_text() == "\n"


def test_resize_discards_contents():
    buf = CellBuffer(4, 2)
    buf.write(0, 0, "abcd")
    buf.resize(6, 3)
    assert (buf.width, buf.height) == (6, 3)
    assert buf.to_text() == "\n\n"


def test_resize_to_the_same_size_keeps_contents():
    # Resize events fire spuriously; repainting on every one would flicker.
    buf = CellBuffer(4, 2)
    buf.write(0, 0, "abcd")
    buf.resize(4, 2)
    assert buf.to_text() == "abcd\n"


def test_get_out_of_bounds_returns_a_blank_cell():
    buf = CellBuffer(2, 2)
    assert buf.get(99, 99) is EMPTY_CELL
    assert buf.get(-1, 0) is EMPTY_CELL


def test_replace_cell_keeps_the_glyph_already_there():
    buf = CellBuffer(3, 1)
    buf.write(0, 0, "x", fg="#fff")
    buf.replace_cell(0, 0, bg="#000")
    assert buf.get(0, 0) == Cell("x", "#fff", "#000")


# ── Groups ──────────────────────────────────────────────────────────
#
# clear_group is the method that has to work: clear() already blanks the frame,
# but a widget dismissed mid-frame must erase itself without disturbing others.


def test_clear_group_erases_only_that_group():
    buf = CellBuffer(10, 2)
    buf.begin_group("one")
    buf.write(0, 0, "aaa")
    buf.begin_group("two")
    buf.write(0, 1, "bbb")

    buf.clear_group("one")
    assert buf.to_text() == "\nbbb"


def test_begin_group_discards_that_groups_previous_cells():
    buf = CellBuffer(10, 1)
    buf.begin_group("hud")
    buf.write(0, 0, "old text")
    buf.begin_group("hud")
    buf.write(0, 0, "new")
    assert buf.to_text() == "new"


def test_writes_outside_any_group_are_untracked():
    buf = CellBuffer(6, 1)
    buf.write(0, 0, "abc")
    buf.clear_group("")
    assert buf.to_text() == "abc"


def test_clear_group_on_an_unknown_group_is_a_no_op():
    buf = CellBuffer(4, 1)
    buf.write(0, 0, "keep")
    buf.clear_group("never-drawn")
    assert buf.to_text() == "keep"


def test_active_group_can_be_resumed_without_wiping():
    # What a widget making several draw calls in one frame needs: accumulate
    # into the group rather than restart it.
    buf = CellBuffer(10, 1)
    buf.begin_group("w")
    buf.write(0, 0, "aa")
    buf.active_group = ""
    buf.write(3, 0, "zz")
    buf.active_group = "w"
    buf.write(6, 0, "bb")

    buf.clear_group("w")
    assert buf.to_text() == "   zz"


def test_clear_forgets_group_membership():
    buf = CellBuffer(6, 1)
    buf.begin_group("g")
    buf.write(0, 0, "abc")
    buf.clear()
    buf.write(0, 0, "xyz")
    buf.clear_group("g")
    assert buf.to_text() == "xyz"


def test_end_group_stops_attribution():
    buf = CellBuffer(8, 1)
    buf.begin_group("g")
    buf.write(0, 0, "aa")
    buf.end_group()
    buf.write(3, 0, "bb")
    buf.clear_group("g")
    assert buf.to_text() == "   bb"


def test_zero_sized_buffer_absorbs_writes():
    # A terminal can report a zero dimension while resizing.
    buf = CellBuffer(0, 0)
    buf.write(0, 0, "anything")
    buf.fill(0, 0, 5, 5, bg="#fff")
    assert buf.to_text() == ""
