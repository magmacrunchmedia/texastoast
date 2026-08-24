"""Renderer tests — these drive a real tkinter canvas and inspect what landed."""
import tkinter as tk

import pytest
from conftest import requires_tk

from texastoast.render.canvas import CanvasRenderer
from texastoast.world.tilemap import TileMap

pytestmark = requires_tk


@pytest.fixture
def renderer(tk_root):
    canvas = tk.Canvas(tk_root, width=64, height=64)
    return CanvasRenderer(canvas, 64, 64)


def _fills(canvas):
    return [canvas.itemcget(i, "fill") for i in canvas.find_all()]


def test_draw_tilemap_renders_tile_zero(renderer):
    # Regression: tile id 0 was hardcoded as "skip", so the grass color every
    # example passes was silently discarded and the background showed through.
    tm = TileMap([[0, 1]], tile_size=16, solid_tiles={1})
    renderer.draw_tilemap(tm, {0: "#7cb342", 1: "#5d4037"})
    fills = _fills(renderer.canvas)
    assert "#7cb342" in fills
    assert "#5d4037" in fills
    assert len(fills) == 2


def test_draw_tilemap_skips_ids_without_a_color(renderer):
    # Unknown ids used to fall back to white, painting bright squares over the
    # map wherever a tile had no entry (including the -1 from a jagged row).
    tm = TileMap([[0, 9]], tile_size=16)
    renderer.draw_tilemap(tm, {0: "#7cb342"})
    fills = _fills(renderer.canvas)
    assert fills == ["#7cb342"]
    assert "#ffffff" not in fills


def test_draw_tilemap_skip_tiles_overrides_a_colored_id(renderer):
    tm = TileMap([[0, 1]], tile_size=16)
    renderer.draw_tilemap(tm, {0: "#7cb342", 1: "#5d4037"}, skip_tiles={0})
    assert _fills(renderer.canvas) == ["#5d4037"]


def test_draw_rect_is_camera_relative(renderer):
    renderer.camera.set_position(10, 20)
    renderer.draw_rect(30, 40, 8, 8, "#e94560")
    x1, y1, x2, y2 = renderer.canvas.coords(renderer.canvas.find_all()[0])
    assert (x1, y1, x2, y2) == (20, 20, 28, 28)


def test_draw_hud_text_ignores_the_camera(renderer):
    renderer.camera.set_position(100, 100)
    renderer.draw_hud_text(4, 4, "score")
    assert renderer.canvas.coords(renderer.canvas.find_all()[0]) == [4, 4]


def test_clear_removes_everything(renderer):
    renderer.draw_rect(0, 0, 4, 4, "#fff")
    renderer.clear()
    assert renderer.canvas.find_all() == ()
