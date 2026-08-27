from texastoast.render.abstract import Renderer, UISurface
from texastoast.render.camera import Camera
from texastoast.render.cellbuffer import Cell, CellBuffer

__all__ = ["CanvasRenderer", "Camera", "Cell", "CellBuffer", "SpriteSheet",
           "TuiRenderer", "load_image", "Renderer", "UISurface"]


def __getattr__(name):
    if name == "CanvasRenderer":
        from texastoast.render.canvas import CanvasRenderer
        return CanvasRenderer
    if name == "SpriteSheet":
        from texastoast.render.sprite import SpriteSheet
        return SpriteSheet
    if name == "load_image":
        from texastoast.render.sprite import load_image
        return load_image
    # Imports no terminal library itself, but stays lazy for symmetry with the
    # other backends: nothing should pay for a backend it does not use.
    if name == "TuiRenderer":
        from texastoast.render.tui import TuiRenderer
        return TuiRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
