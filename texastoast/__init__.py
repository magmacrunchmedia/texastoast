"""texastoast — Python RPG engine and Magma Hub I2C layer."""

__version__ = "0.1.0"


def __getattr__(name):
    if name in ("Config", "GameLoop", "Game"):
        from texastoast.core import Config, GameLoop, Game
        return {"Config": Config, "GameLoop": GameLoop, "Game": Game}[name]

    if name in ("CanvasRenderer", "Camera", "SpriteSheet"):
        from texastoast.render import CanvasRenderer, Camera, SpriteSheet
        return {"CanvasRenderer": CanvasRenderer, "Camera": Camera, "SpriteSheet": SpriteSheet}[name]

    if name in ("TileMap", "Entity", "AABB"):
        from texastoast.world import TileMap, Entity, AABB
        return {"TileMap": TileMap, "Entity": Entity, "AABB": AABB}[name]

    if name in ("InputState", "KeyboardInput"):
        from texastoast.input import InputState, KeyboardInput
        return {"InputState": InputState, "KeyboardInput": KeyboardInput}[name]

    if name in ("DialogueBox", "Menu", "HUD"):
        from texastoast.ui import DialogueBox, Menu, HUD
        return {"DialogueBox": DialogueBox, "Menu": Menu, "HUD": HUD}[name]

    raise AttributeError(f"module 'texastoast' has no attribute {name!r}")


__all__ = [
    "Config",
    "GameLoop",
    "Game",
    "CanvasRenderer",
    "Camera",
    "SpriteSheet",
    "TileMap",
    "Entity",
    "AABB",
    "InputState",
    "KeyboardInput",
    "DialogueBox",
    "Menu",
    "HUD",
]
