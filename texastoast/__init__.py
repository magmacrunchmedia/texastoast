"""texastoast — Python RPG engine with I2C hardware abstraction."""

__version__ = "0.4.0"


def __getattr__(name):
    if name in ("Config", "GameLoop", "Game"):
        from texastoast.core import Config, Game, GameLoop
        return {"Config": Config, "GameLoop": GameLoop, "Game": Game}[name]

    if name in ("CanvasRenderer", "Camera", "SpriteSheet", "Renderer", "UISurface"):
        from texastoast.render import Camera, CanvasRenderer, Renderer, SpriteSheet, UISurface
        return {"CanvasRenderer": CanvasRenderer, "Camera": Camera,
                "SpriteSheet": SpriteSheet, "Renderer": Renderer,
                "UISurface": UISurface}[name]

    if name in ("TileMap", "Entity", "AABB"):
        from texastoast.world import AABB, Entity, TileMap
        return {"TileMap": TileMap, "Entity": Entity, "AABB": AABB}[name]

    if name in ("InputState", "KeyboardInput", "MagmaHubInput", "CompositeInput",
                "InputRecorder", "ReplayInput"):
        # getattr, not a from-import: importing the whole group would pull in
        # KeyboardInput (and with it tkinter) to answer for InputRecorder.
        from texastoast import input as input_pkg
        return getattr(input_pkg, name)

    if name in ("I2CBus", "MagmaHub", "ControllerState", "HubStats",
                "SimBus", "simulated_hub", "KeyboardHubDriver",
                "HubPoller", "scan_buses_async"):
        from texastoast import i2c
        return getattr(i2c, name)

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
    "Renderer",
    "UISurface",
    "TileMap",
    "Entity",
    "AABB",
    "InputState",
    "KeyboardInput",
    "MagmaHubInput",
    "CompositeInput",
    "InputRecorder",
    "ReplayInput",
    "I2CBus",
    "MagmaHub",
    "ControllerState",
    "HubStats",
    "SimBus",
    "simulated_hub",
    "KeyboardHubDriver",
    "HubPoller",
    "scan_buses_async",
    "DialogueBox",
    "Menu",
    "HUD",
]
