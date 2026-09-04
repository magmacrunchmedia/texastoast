"""Renderer/UISurface protocol conformance.

The seam that a future SDL/framebuffer backend will implement. What matters
now is that CanvasRenderer satisfies both protocols structurally, and that
group-scoped drawing keeps the tag-composition behaviour the UI relies on.
"""
import pytest

# See test_render.py: skips a missing tkinter, where requires_tk skips a
# missing display. Both conditions have to be handled to collect on a Pi.
tk = pytest.importorskip("tkinter", reason="tkinter is not installed")

from conftest import requires_tk

from texastoast.render.abstract import Renderer, UISurface, as_ui_surface
from texastoast.render.canvas import CanvasRenderer


@pytest.fixture
def canvas(tk_root):
    c = tk.Canvas(tk_root, width=400, height=300)
    c.pack()
    return c


@requires_tk
def test_canvas_renderer_satisfies_both_protocols(canvas):
    renderer = CanvasRenderer(canvas, 400, 300)
    assert isinstance(renderer, Renderer)
    assert isinstance(renderer, UISurface)


@requires_tk
def test_renderer_exposes_its_dimensions(canvas):
    renderer = CanvasRenderer(canvas, 400, 300)
    assert renderer.width == 400
    assert renderer.height == 300


@requires_tk
def test_present_is_a_no_op(canvas):
    renderer = CanvasRenderer(canvas, 400, 300)
    renderer.ui_rect(0, 0, 10, 10, fill="#fff", group="g")
    renderer.present()
    assert canvas.find_withtag("g")


@requires_tk
def test_begin_group_clears_only_its_own_group(canvas):
    renderer = CanvasRenderer(canvas, 400, 300)
    renderer.ui_rect(0, 0, 10, 10, fill="#fff", group="one")
    renderer.ui_text(20, 20, "hi", fill="#fff", group="two")
    assert canvas.find_withtag("one")
    assert canvas.find_withtag("two")

    renderer.begin_group("one")
    assert not canvas.find_withtag("one")
    assert canvas.find_withtag("two")


@requires_tk
def test_as_ui_surface_wraps_a_bare_canvas(canvas):
    surface = as_ui_surface(canvas, 400, 300)
    assert isinstance(surface, UISurface)
    assert surface.width == 400
    surface.ui_rect(0, 0, 10, 10, fill="#fff", group="g")
    assert canvas.find_withtag("g")
    surface.clear_group("g")
    assert not canvas.find_withtag("g")


@requires_tk
def test_as_ui_surface_passes_a_surface_through(canvas):
    renderer = CanvasRenderer(canvas, 400, 300)
    assert as_ui_surface(renderer, None, None) is renderer


def test_as_ui_surface_defaults_dimensions_headlessly():
    class FakeCanvas:
        def delete(self, tag):
            pass

        def create_rectangle(self, *a, **k):
            pass

        def create_text(self, *a, **k):
            pass

    surface = as_ui_surface(FakeCanvas(), None, None)
    assert surface.width == 640
    assert surface.height == 480
