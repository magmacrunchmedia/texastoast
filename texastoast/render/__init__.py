from texastoast.render.abstract import Renderer, UISurface
from texastoast.render.camera import Camera

__all__ = ["CanvasRenderer", "Camera", "SpriteSheet", "load_image",
           "Renderer", "UISurface"]


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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
