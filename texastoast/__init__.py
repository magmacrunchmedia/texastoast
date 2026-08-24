"""texastoast — Python RPG engine with I2C hardware abstraction."""

__version__ = "0.3.0"


def __getattr__(name):
    if name in ("Config", "GameLoop", "Game"):
        from texastoast.core import Config, Game, GameLoop
        return {"Config": Config, "GameLoop": GameLoop, "Game": Game}[name]

    if name in ("CanvasRenderer", "Camera", "SpriteSheet"):
        from texastoast.render import Camera, CanvasRenderer, SpriteSheet
        return {"CanvasRenderer": CanvasRenderer, "Camera": Camera, "SpriteSheet": SpriteSheet}[name]

    if name in ("TileMap", "Entity", "AABB"):
        from texastoast.world import AABB, Entity, TileMap
        return {"TileMap": TileMap, "Entity": Entity, "AABB": AABB}[name]

    if name in ("InputState", "KeyboardInput", "MagmaHubInput", "CompositeInput"):
        from texastoast.input import CompositeInput, InputState, KeyboardInput, MagmaHubInput
        return {"InputState": InputState, "KeyboardInput": KeyboardInput,
                "MagmaHubInput": MagmaHubInput, "CompositeInput": CompositeInput}[name]

    if name in ("I2CBus", "MagmaHub", "ControllerState"):
        from texastoast.i2c import ControllerState, I2CBus, MagmaHub
        return {"I2CBus": I2CBus, "MagmaHub": MagmaHub, "ControllerState": ControllerState}[name]

    if name in ("DialogueBox", "Menu", "HUD"):
        from texastoast.ui import HUD, DialogueBox, Menu
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
    "MagmaHubInput",
    "CompositeInput",
    "I2CBus",
    "MagmaHub",
    "ControllerState",
    "DialogueBox",
    "Menu",
    "HUD",
]
