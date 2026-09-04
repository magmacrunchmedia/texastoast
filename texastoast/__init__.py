"""texastoast — Python RPG engine with I2C hardware abstraction."""

__version__ = "0.11.2"


def __getattr__(name):
    if name in ("Config", "GameLoop", "Game"):
        # getattr, not a from-import: the group resolves every name it lists, so
        # a from-import here pulled Game (and with it tkinter) in to answer for
        # Config and GameLoop, neither of which has ever needed it.
        from texastoast import core
        return getattr(core, name)

    if name in ("ArcadeGame", "GameInfo", "Host", "discover_games"):
        from texastoast import arcade
        return arcade.discover if name == "discover_games" else getattr(arcade, name)

    if name in ("Scheduler", "ManualScheduler", "TuiGame", "GameSurface",
                "TuiInput", "TextualScheduler", "TuiHost"):
        # getattr, not a from-import: the terminal names live behind core's own
        # lazy hook so that asking for ManualScheduler does not import Textual.
        from texastoast import core
        return getattr(core, name)

    if name in ("Scene", "SceneStack"):
        from texastoast import scene
        return getattr(scene, name)

    if name == "Mixer":
        from texastoast.audio import Mixer
        return Mixer

    if name in ("CanvasRenderer", "Camera", "SpriteSheet", "Renderer", "UISurface",
                "TuiRenderer", "CellBuffer", "Cell"):
        # getattr for the same reason as above: a from-import of the group
        # would pull CanvasRenderer (and tkinter) in to answer for CellBuffer.
        from texastoast import render
        return getattr(render, name)

    if name in ("TileMap", "Entity", "AABB", "EntityGroup"):
        from texastoast import world
        return getattr(world, name)

    if name in ("InputState", "KeyboardInput", "MagmaHubInput", "CompositeInput",
                "InputRecorder", "ReplayInput", "Player", "PlayerManager"):
        # getattr, not a from-import: importing the whole group would pull in
        # KeyboardInput (and with it tkinter) to answer for InputRecorder.
        from texastoast import input as input_pkg
        return getattr(input_pkg, name)

    if name in ("I2CBus", "MagmaHub", "ControllerState", "HubStats",
                "SimBus", "simulated_hub", "KeyboardHubDriver",
                "HubPoller", "scan_buses_async"):
        from texastoast import i2c
        return getattr(i2c, name)

    if name in ("DialogueBox", "Menu", "HUD", "Theme", "DEFAULT_THEME"):
        from texastoast import ui
        return getattr(ui, name)

    raise AttributeError(f"module 'texastoast' has no attribute {name!r}")


__all__ = [
    "Config",
    "GameLoop",
    "Game",
    "Scheduler",
    "ManualScheduler",
    "TuiGame",
    "GameSurface",
    "TuiInput",
    "TextualScheduler",
    "TuiHost",
    "ArcadeGame",
    "GameInfo",
    "Host",
    "discover_games",
    "Scene",
    "SceneStack",
    "Mixer",
    "EntityGroup",
    "Player",
    "PlayerManager",
    "Theme",
    "DEFAULT_THEME",
    "CanvasRenderer",
    "TuiRenderer",
    "CellBuffer",
    "Cell",
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
