"""The magmascript binding — the engine, exposed to ``.mgs`` scripts.

This module imports nothing from magmascript. It is discovered through the
``magmascript.domains`` entry point declared in ``pyproject.toml``, so installing
texastoast alongside magmascript is all it takes::

    g = texastoast.game({"title": "Demo", "width": 400, "height": 300})
    r = texastoast.renderer(g, 400, 300)
    kb = texastoast.keyboard(g)
    ...
    g.start()

The domain is named ``texastoast`` rather than ``toast``: magmascript's CLI
already spells ``magmascript toast <target>`` for clearing caches, and one name
meaning two things in one tool is worse than a longer one.

Two things shape the API here, both properties of the language rather than of
the engine:

* **Options arrive as a dict, not keyword arguments.** MagmaScript has no
  keyword-argument syntax, so ``toast.game({"title": ...})`` is the closest
  spelling to ``Game(title=...)``. Unknown keys are an error rather than a
  silent default, since a typo is otherwise invisible.
* **Engine objects are returned bare.** The interpreter reaches host objects
  through ``getattr``, which is all a plain class needs. Nothing here wraps or
  copies; ``p.x`` in a script is the same attribute as ``entity.x`` in Python.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from texastoast.audio.mixer import Mixer
from texastoast.core.game import Game
from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.poller import HubPoller
from texastoast.i2c.sim import simulated_hub
from texastoast.input.keyboard import KeyboardInput
from texastoast.input.magma_hub import CompositeInput, MagmaHubInput
from texastoast.input.players import PlayerManager
from texastoast.input.recording import InputRecorder, ReplayInput
from texastoast.render.canvas import CanvasRenderer
from texastoast.render.sprite import SpriteSheet
from texastoast.scene import SceneStack
from texastoast.ui.dialogue import DialogueBox
from texastoast.ui.hud import HUD
from texastoast.ui.menu import Menu
from texastoast.ui.theme import DEFAULT_THEME, Theme
from texastoast.world.entity import Entity
from texastoast.world.group import EntityGroup
from texastoast.world.tilemap import TileMap

__all__ = ["TexastoastDomain"]


def _num(value: Any) -> Any:
    """Unwrap an Asthenosphere fixed-width value to a plain number.

    A script may reasonably write ``i32(100)`` for a speed. Handing that
    straight to the engine breaks the first ``math.hypot`` it reaches, so
    widths are stripped at the boundary. Duck-typed rather than imported:
    this module does not depend on magmascript.
    """
    spec = getattr(value, "spec", None)
    if spec is not None and hasattr(value, "value"):
        return value.value
    return value


def _options(opts: Any, allowed: dict[str, Any], who: str) -> dict[str, Any]:
    """Validate an options dict against ``allowed`` and fill in the defaults."""
    if opts is None:
        return dict(allowed)
    if not isinstance(opts, dict):
        raise TypeError(f"{who} expected a dict of options, got {type(opts).__name__}")

    unknown = set(opts) - set(allowed)
    if unknown:
        raise ValueError(
            f"{who} got unknown option{'s' if len(unknown) > 1 else ''} "
            f"{', '.join(repr(k) for k in sorted(unknown))}. "
            f"Valid options: {', '.join(sorted(allowed))}"
        )

    resolved = dict(allowed)
    resolved.update({key: _num(value) for key, value in opts.items()})
    return resolved


class TexastoastDomain:
    """texastoast, exposed to ``.mgs`` scripts as ``texastoast`` (or ``tt``).

    Constructing this does nothing — no window, no canvas, no tkinter import
    beyond what the package already did. magmascript builds a domain's client
    lazily, but even so, a REPL that merely mentions the domain must not open a
    window.
    """

    def __init__(self, config: Any = None):
        # magmascript passes its own Config. texastoast has no use for it.
        self._config = config

    # ── core ────────────────────────────────────────────────────────

    def game(self, opts: dict | None = None) -> Game:
        o = _options(opts, {
            "title": "texastoast",
            "width": 640,
            "height": 480,
            "fps": 30,
            "max_consecutive_errors": 10,
        }, "texastoast.game()")
        return Game(
            title=str(o["title"]),
            width=int(o["width"]),
            height=int(o["height"]),
            fps=int(o["fps"]),
            max_consecutive_errors=int(o["max_consecutive_errors"]),
        )

    def renderer(self, game: Game, width: int, height: int) -> CanvasRenderer:
        return CanvasRenderer(game.canvas, int(_num(width)), int(_num(height)))

    def keyboard(self, game: Game) -> KeyboardInput:
        return KeyboardInput(game.root)

    # ── world ───────────────────────────────────────────────────────

    def tilemap(self, grid, tile_size: int = 16, solid=None) -> TileMap:
        """Build a tile map. ``solid`` is any list of solid tile ids."""
        rows = [[int(_num(cell)) for cell in row] for row in grid]
        solid_ids = [int(_num(t)) for t in solid] if solid is not None else None
        return TileMap(rows, tile_size=int(_num(tile_size)), solid_tiles=solid_ids)

    def entity(self, opts: dict | None = None) -> Entity:
        o = _options(opts, {
            "x": 0, "y": 0, "width": 16, "height": 16, "speed": 1.0,
        }, "texastoast.entity()")
        return Entity(
            x=float(o["x"]), y=float(o["y"]),
            width=float(o["width"]), height=float(o["height"]),
            speed=float(o["speed"]),
        )

    # ── ui ──────────────────────────────────────────────────────────
    # Each accepts a Game (draws on its canvas, pre-0.4 style) or a renderer
    # (any UISurface): with a renderer, width/height default from it instead
    # of being repeated by hand.

    @staticmethod
    def _surface_of(target: Any) -> Any:
        return target if hasattr(target, "ui_rect") else target.canvas

    def dialogue(self, game: Any, opts: dict | None = None) -> DialogueBox:
        o = _options(opts, {
            "width": None, "height": None, "box_height": 100,
            "padding": 12, "speed": 0.03, "theme": None,
        }, "texastoast.dialogue()")
        return DialogueBox(
            self._surface_of(game),
            width=None if o["width"] is None else int(o["width"]),
            height=None if o["height"] is None else int(o["height"]),
            box_height=int(o["box_height"]), padding=int(o["padding"]),
            speed=float(o["speed"]), theme=o["theme"],
        )

    def menu(self, game: Any, opts: dict | None = None) -> Menu:
        o = _options(opts, {
            "width": None, "height": None,
            "selected_color": None, "normal_color": None,
            "disabled_color": None, "item_padding": 8, "theme": None,
        }, "texastoast.menu()")
        return Menu(
            self._surface_of(game),
            width=None if o["width"] is None else int(o["width"]),
            height=None if o["height"] is None else int(o["height"]),
            selected_color=None if o["selected_color"] is None else str(o["selected_color"]),
            normal_color=None if o["normal_color"] is None else str(o["normal_color"]),
            disabled_color=None if o["disabled_color"] is None else str(o["disabled_color"]),
            item_padding=int(o["item_padding"]), theme=o["theme"],
        )

    def hud(self, game: Any, opts: dict | None = None) -> HUD:
        o = _options(opts, {"width": None, "height": None, "padding": 8,
                            "theme": None},
                     "texastoast.hud()")
        return HUD(
            self._surface_of(game),
            width=None if o["width"] is None else int(o["width"]),
            height=None if o["height"] is None else int(o["height"]),
            padding=int(o["padding"]), theme=o["theme"],
        )

    def theme(self, opts: dict | None = None) -> Theme:
        """A widget theme. Options are the Theme fields; omitted ones keep
        the engine defaults."""
        defaults = dataclasses.asdict(DEFAULT_THEME)
        o = _options(opts, defaults, "texastoast.theme()")
        return Theme(**{k: o[k] for k in defaults})

    # ── structure ───────────────────────────────────────────────────

    def scenes(self) -> SceneStack:
        """A scene stack. The script wires it itself:
        ``g.set_update(s.update)``, ``g.set_render(s.render)``."""
        return SceneStack()

    def entities(self) -> EntityGroup:
        return EntityGroup()

    def sprite_sheet(self, path: Any, frame_width: Any,
                     frame_height: Any) -> SpriteSheet:
        """A sprite sheet. Frames are fetched with the game's root:
        ``sheet.get_frame(g.root, col, row)``."""
        return SpriteSheet(str(path), int(_num(frame_width)),
                           int(_num(frame_height)))

    # ── audio ───────────────────────────────────────────────────────

    def mixer(self) -> Mixer:
        """An audio mixer on the best backend this machine offers. Wire
        teardown yourself: ``g.on_close(m.close)``."""
        return Mixer()

    # ── players ─────────────────────────────────────────────────────

    def players(self, opts: dict | None = None) -> PlayerManager:
        o = _options(opts, {"max_players": 4, "join_buttons": ("a", "start")},
                     "texastoast.players()")
        return PlayerManager(
            max_players=int(o["max_players"]),
            join_buttons=tuple(str(b) for b in o["join_buttons"]),
        )

    # ── hardware ────────────────────────────────────────────────────
    # The dev-kit workflows, scriptable: real hubs, simulated hubs,
    # background polling, and record/replay.

    def hub(self, opts: dict | None = None) -> MagmaHub:
        o = _options(opts, {
            "address": 0x08, "bus": 1, "controllers": 1, "poll_interval": 0.016,
        }, "texastoast.hub()")
        return MagmaHub(
            int(o["address"]),
            I2CBus(int(o["bus"])),
            num_controllers=int(o["controllers"]),
            poll_interval=float(o["poll_interval"]),
        )

    def hubs(self, opts: dict | None = None) -> list:
        o = _options(opts, {
            "buses": None, "addresses": None, "controllers": 1,
        }, "texastoast.hubs()")
        buses = None if o["buses"] is None else [int(_num(b)) for b in o["buses"]]
        addresses = (None if o["addresses"] is None
                     else [int(_num(a)) for a in o["addresses"]])
        return MagmaHub.scan_buses(
            bus_numbers=buses, addresses=addresses,
            num_controllers=int(o["controllers"]),
        )

    def sim_hub(self, opts: dict | None = None) -> MagmaHub:
        """A simulated hub. The SimBus is reachable as ``hub.sim`` so scripts
        can drive it: ``h.sim.set_buttons(8, 0, 16)``."""
        o = _options(opts, {"address": 0x08, "controllers": 1},
                     "texastoast.sim_hub()")
        hub, sim = simulated_hub(
            num_controllers=int(o["controllers"]), address=int(o["address"]),
        )
        hub.sim = sim
        return hub

    def hub_input(self, hub: Any, index: int = 0) -> MagmaHubInput:
        return MagmaHubInput(hub, controller_index=int(_num(index)))

    def composite(self, keyboard: Any = None,
                  hub_input: Any = None) -> CompositeInput:
        return CompositeInput(keyboard, hub_input)

    def poller(self, hub: Any, opts: dict | None = None) -> HubPoller:
        """A background poller for ``hub``. Started unless ``start`` is False;
        wire ``g.on_close(p.stop)`` yourself — the engine provides the pieces,
        the script wires them together."""
        o = _options(opts, {"poll_interval": 0.008, "start": True},
                     "texastoast.poller()")
        p = HubPoller(hub, poll_interval=float(o["poll_interval"]))
        if o["start"]:
            p.start()
        return p

    def recorder(self, source: Any, path: Any = None) -> InputRecorder:
        return InputRecorder(source, path=None if path is None else str(path))

    def replay(self, path: Any, opts: dict | None = None) -> ReplayInput:
        o = _options(opts, {"loop": False}, "texastoast.replay()")
        return ReplayInput(str(path), loop=bool(o["loop"]))

    def version(self) -> str:
        from texastoast import __version__
        return __version__

    def __repr__(self) -> str:
        return "<texastoast>"
