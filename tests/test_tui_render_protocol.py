"""TuiRenderer conformance — the terminal counterpart to test_render_protocol.py.

Most of this runs with nothing installed: TuiRenderer draws into a CellBuffer
and imports no terminal library, which is exactly the property that lets a
future ANSI backend reuse it. The handful of tests that need Textual are
skipped when the ``tui`` extra is absent.
"""

import pytest

from texastoast.render.abstract import Renderer, UISurface, as_ui_surface
from texastoast.render.cellbuffer import CellBuffer
from texastoast.render.tui import FULL_BLOCK, TuiRenderer


def _has_textual() -> bool:
    try:
        import textual  # noqa: F401
    except ImportError:
        return False
    return True


requires_textual = pytest.mark.skipif(
    not _has_textual(), reason='needs the tui extra: pip install "texastoast[tui]"'
)


@pytest.fixture
def renderer():
    return TuiRenderer(20, 6)


# ── Protocol conformance ────────────────────────────────────────────


def test_tui_renderer_satisfies_both_protocols(renderer):
    assert isinstance(renderer, Renderer)
    assert isinstance(renderer, UISurface)


def test_as_ui_surface_passes_a_tui_renderer_through(renderer):
    assert as_ui_surface(renderer, None, None) is renderer


def test_renderer_exposes_its_dimensions_in_cells(renderer):
    assert renderer.width == 20
    assert renderer.height == 6
    assert renderer.camera.width == 20


def test_importing_the_backend_pulls_no_terminal_library():
    import sys

    import texastoast.render.tui  # noqa: F401

    # The whole point of the surface-injection design.
    assert "textual" not in sys.modules or _has_textual()
    assert "curses" not in sys.modules


# ── present() ───────────────────────────────────────────────────────


def test_present_flushes_to_the_surface():
    # Unlike the tkinter backend, present() is NOT a no-op here — the buffer is
    # off-screen and nothing is visible until it is pushed.
    flushed = []

    class Surface:
        def flush(self, buffer):
            flushed.append(buffer.to_text())

    renderer = TuiRenderer(6, 1, surface=Surface())
    renderer.draw_hud_text(0, 0, "hi")
    renderer.present()
    assert flushed == ["hi"]


def test_present_without_a_surface_is_safe():
    TuiRenderer(4, 1).present()


def test_clear_blanks_the_frame(renderer):
    renderer.draw_hud_text(0, 0, "text")
    renderer.clear()
    assert renderer.to_text().strip() == ""


# ── Drawing ─────────────────────────────────────────────────────────


def test_draw_rect_fills_with_background(renderer):
    renderer.draw_rect(2, 1, 3, 2, "#ff0000")
    assert renderer.buffer.get(2, 1).bg == "#ff0000"
    assert renderer.buffer.get(4, 2).bg == "#ff0000"
    assert renderer.buffer.get(5, 1).bg is None


def test_draw_text_is_offset_by_the_camera(renderer):
    renderer.camera.set_position(3, 1)
    renderer.draw_text(5, 2, "ab")
    assert renderer.buffer.get(2, 1).char == "a"


def test_draw_hud_text_ignores_the_camera(renderer):
    renderer.camera.set_position(3, 1)
    renderer.draw_hud_text(5, 2, "ab")
    assert renderer.buffer.get(5, 2).char == "a"


def test_draw_text_accepts_and_ignores_tk_only_kwargs(renderer):
    # Games ported from the canvas backend pass these; erroring would force a
    # backend check at every call site.
    renderer.draw_hud_text(0, 0, "x", font=("Courier", 10), fill="#abcdef")
    assert renderer.buffer.get(0, 0).fg == "#abcdef"


@pytest.mark.parametrize(
    "anchor,expected_x",
    [("nw", 10), ("n", 8), ("ne", 6), ("w", 10), ("center", 8), ("e", 6)],
)
def test_text_anchors_position_on_the_grid(anchor, expected_x):
    renderer = TuiRenderer(20, 3)
    renderer.draw_hud_text(10, 1, "abcd", anchor=anchor)
    assert renderer.buffer.get(expected_x, 1).char == "a"


def test_draw_image_is_a_no_op(renderer):
    renderer.draw_image(0, 0, object())
    assert renderer.to_text().strip() == ""


def test_draw_image_warns_only_once(renderer, caplog):
    import logging

    with caplog.at_level(logging.DEBUG, logger="texastoast.render.tui"):
        renderer.draw_image(0, 0, object())
        renderer.draw_image(0, 0, object())
    assert len([r for r in caplog.records if "draw_image" in r.message]) == 1


# ── Tilemaps ────────────────────────────────────────────────────────


class FakeTileMap:
    tile_size = 16

    def __init__(self, grid):
        self._grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])

    def get(self, col, row):
        return self._grid[row][col]


def test_draw_tilemap_paints_one_cell_per_tile():
    # One cell per tile regardless of tile_size: 16 pixels means nothing here,
    # and scaling by it would push a small map entirely off-screen.
    renderer = TuiRenderer(4, 2)
    tilemap = FakeTileMap([[1, 1, 0, 1], [0, 1, 1, 0]])
    renderer.draw_tilemap(tilemap, {1: "#00ff00"})
    assert renderer.to_text() == f"{FULL_BLOCK*2} {FULL_BLOCK}\n {FULL_BLOCK*2}"


def test_draw_tilemap_honours_custom_glyphs():
    renderer = TuiRenderer(3, 1)
    renderer.tile_glyphs = {1: "#", 2: "~"}
    tilemap = FakeTileMap([[1, 2, 1]])
    renderer.draw_tilemap(tilemap, {1: "#fff", 2: "#00f"})
    assert renderer.to_text() == "#~#"


def test_draw_tilemap_skips_requested_ids():
    renderer = TuiRenderer(3, 1)
    tilemap = FakeTileMap([[1, 1, 1]])
    renderer.draw_tilemap(tilemap, {1: "#fff"}, skip_tiles=[1])
    assert renderer.to_text() == ""


def test_draw_tilemap_ignores_ids_with_no_color():
    renderer = TuiRenderer(3, 1)
    renderer.tile_glyphs = {1: "#"}
    tilemap = FakeTileMap([[1, 9, 1]])
    renderer.draw_tilemap(tilemap, {1: "#fff"})
    assert renderer.to_text() == "# #"


# ── UISurface ───────────────────────────────────────────────────────


def test_ui_rect_fills_and_outlines(renderer):
    renderer.ui_rect(0, 0, 4, 3, fill="#111111", outline="#ffffff", outline_width=1)
    assert renderer.buffer.get(1, 1).bg == "#111111"
    assert renderer.buffer.get(0, 0).bg == "#ffffff"


def test_ui_rect_without_outline_width_still_fills(renderer):
    renderer.ui_rect(0, 0, 3, 2, fill="#222222")
    assert renderer.buffer.get(2, 1).bg == "#222222"


def test_clear_group_erases_only_that_widget(renderer):
    renderer.ui_text(0, 0, "alpha", fill="#fff", group="one")
    renderer.ui_text(0, 1, "beta", fill="#fff", group="two")
    renderer.clear_group("one")
    assert renderer.to_text().rstrip("\n") == "\nbeta"


def test_begin_group_restarts_a_widgets_drawing(renderer):
    renderer.begin_group("hud")
    renderer.ui_text(0, 0, "old", fill="#fff", group="hud")
    renderer.begin_group("hud")
    renderer.ui_text(0, 0, "new", fill="#fff", group="hud")
    assert renderer.to_text().split("\n")[0] == "new"


def test_a_widget_accumulates_across_several_draw_calls(renderer):
    # begin_group once, then several draws — none of which may wipe the others.
    renderer.begin_group("w")
    renderer.ui_rect(0, 0, 5, 1, fill="#000", group="w")
    renderer.ui_text(0, 0, "hey", fill="#fff", group="w")
    assert renderer.to_text().split("\n")[0] == "hey"
    renderer.clear_group("w")
    assert renderer.to_text().strip() == ""


def test_ui_text_wraps_to_the_given_width(renderer):
    renderer.ui_text(0, 0, "aaa bbb ccc", fill="#fff", width=7)
    assert renderer.to_text().startswith("aaa bbb\nccc")


def test_ui_text_ignores_the_font_argument(renderer):
    renderer.ui_text(0, 0, "x", fill="#fff", font=("Courier", 24))
    assert renderer.buffer.get(0, 0).char == "x"


# ── Resize ──────────────────────────────────────────────────────────


def test_resize_updates_the_renderer_and_camera(renderer):
    renderer.resize(40, 10)
    assert (renderer.width, renderer.height) == (40, 10)
    assert (renderer.camera.width, renderer.camera.height) == (40, 10)


def test_an_injected_buffer_is_used_as_is():
    buffer = CellBuffer(5, 1)
    renderer = TuiRenderer(5, 1, buffer=buffer)
    renderer.draw_hud_text(0, 0, "ok")
    assert buffer.to_text() == "ok"


# ── Textual host ────────────────────────────────────────────────────


@requires_textual
def test_textual_scheduler_satisfies_the_scheduler_protocol():
    from texastoast.core.scheduler import Scheduler
    from texastoast.core.tui_game import TextualScheduler

    assert isinstance(TextualScheduler(None), Scheduler)


@requires_textual
def test_after_cancel_tolerates_a_dead_timer():
    from texastoast.core.tui_game import TextualScheduler

    class Boom:
        def stop(self):
            raise RuntimeError("already gone")

    TextualScheduler(None).after_cancel(Boom())
    TextualScheduler(None).after_cancel(None)


@requires_textual
def test_scheduler_converts_milliseconds_to_seconds():
    from texastoast.core.tui_game import TextualScheduler

    seen = []

    class FakeApp:
        def set_timer(self, delay, callback):
            seen.append(delay)
            return "timer"

    TextualScheduler(FakeApp()).after(250, lambda: None)
    assert seen == [0.25]


@requires_textual
def test_game_surface_renders_a_line_of_the_buffer():
    from texastoast.core.tui_game import GameSurface

    buffer = CellBuffer(5, 2)
    buffer.write(0, 0, "hi", fg="#ff0000")
    surface = GameSurface(buffer)

    strip = surface.render_line(0)
    assert "".join(seg.text for seg in strip._segments) == "hi   "


@requires_textual
def test_game_surface_coalesces_runs_of_identical_style():
    from texastoast.core.tui_game import GameSurface

    buffer = CellBuffer(6, 1)
    buffer.write(0, 0, "aaa", fg="#ff0000")
    buffer.write(3, 0, "bbb", fg="#00ff00")
    surface = GameSurface(buffer)

    strip = surface.render_line(0)
    # Two runs, not six single-character segments.
    assert len(strip._segments) == 2


@requires_textual
def test_tui_game_normalizes_tkinter_key_sequences():
    from texastoast.core.tui_game import TuiGame

    assert TuiGame._normalize_key("<Left>") == "left"
    assert TuiGame._normalize_key("<KeyPress-a>") == "a"
    assert TuiGame._normalize_key("space") == "space"


@requires_textual
def test_tui_game_exposes_a_renderer_over_its_surface():
    from texastoast.core.tui_game import TuiGame

    game = TuiGame(width=10, height=3)
    assert isinstance(game.renderer, Renderer)
    assert isinstance(game.renderer, UISurface)
    game.renderer.draw_hud_text(0, 0, "hey")
    game.renderer.present()
    assert game.surface.buffer.to_text().startswith("hey")
