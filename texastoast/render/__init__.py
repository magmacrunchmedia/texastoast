from texastoast import _lazy
from texastoast.render.abstract import Renderer, UISurface
from texastoast.render.camera import Camera
from texastoast.render.cellbuffer import Cell, CellBuffer

__all__ = ["CanvasRenderer", "Camera", "Cell", "CellBuffer", "SpriteSheet",
           "TuiRenderer", "load_image", "Renderer", "UISurface"]


def __getattr__(name):
    if name == "CanvasRenderer":
        try:
            from texastoast.render.canvas import CanvasRenderer
        except ImportError as exc:  # pragma: no cover - depends on install
            _lazy.reraise_tk(name, exc)
            raise
        return CanvasRenderer
    if name in ("SpriteSheet", "load_image"):
        try:
            from texastoast.render import sprite
        except ImportError as exc:  # pragma: no cover - depends on install
            _lazy.reraise_tk(name, exc)
            raise
        return getattr(sprite, name)
    # Imports no terminal library itself, but stays lazy for symmetry with the
    # other backends: nothing should pay for a backend it does not use.
    if name == "TuiRenderer":
        from texastoast.render.tui import TuiRenderer
        return TuiRenderer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
