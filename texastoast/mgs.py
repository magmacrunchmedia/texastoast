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

from typing import Any

from texastoast.core.game import Game
from texastoast.input.keyboard import KeyboardInput
from texastoast.render.canvas import CanvasRenderer
from texastoast.ui.dialogue import DialogueBox
from texastoast.ui.hud import HUD
from texastoast.ui.menu import Menu
from texastoast.world.entity import Entity
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

    def dialogue(self, game: Game, opts: dict | None = None) -> DialogueBox:
        o = _options(opts, {
            "width": 640, "height": 480, "box_height": 100,
            "padding": 12, "speed": 0.03,
        }, "texastoast.dialogue()")
        return DialogueBox(
            game.canvas,
            width=int(o["width"]), height=int(o["height"]),
            box_height=int(o["box_height"]), padding=int(o["padding"]),
            speed=float(o["speed"]),
        )

    def menu(self, game: Game, opts: dict | None = None) -> Menu:
        o = _options(opts, {
            "width": 640, "height": 480,
            "selected_color": "#e94560", "normal_color": "#ffffff",
            "disabled_color": "#555555", "item_padding": 8,
        }, "texastoast.menu()")
        return Menu(
            game.canvas,
            width=int(o["width"]), height=int(o["height"]),
            selected_color=str(o["selected_color"]),
            normal_color=str(o["normal_color"]),
            disabled_color=str(o["disabled_color"]),
            item_padding=int(o["item_padding"]),
        )

    def hud(self, game: Game, opts: dict | None = None) -> HUD:
        o = _options(opts, {"width": 640, "height": 480, "padding": 8},
                     "texastoast.hud()")
        return HUD(
            game.canvas,
            width=int(o["width"]), height=int(o["height"]),
            padding=int(o["padding"]),
        )

    def version(self) -> str:
        from texastoast import __version__
        return __version__

    def __repr__(self) -> str:
        return "<texastoast>"
