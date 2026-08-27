"""A terminal host — owns the screen so a game does not have to.

The concrete counterpart to :class:`texastoast.arcade.Host`. That module names
the contract and imports nothing; this one implements it over
:class:`~texastoast.core.tui_game.TuiGame`, and therefore needs the ``tui``
extra.

Everything here is generic. Building the terminal, holding the scene stack,
draining keys into the top scene, pushing and popping — none of it is any
particular game's business, and all of it is identical for a game run on its
own and for a game seated by a launcher. Writing it once is the difference
between a launcher being a menu and a launcher being a second copy of every
game's wiring.

A game shipped as its own command uses this directly::

    host = TuiHost.for_game(GAME)
    host.run()

and a launcher uses the same object to seat whichever game was chosen, which is
why :meth:`seat` applies the game's declared frame rate and input behaviour
rather than assuming the host's.
"""

from __future__ import annotations

from typing import Any

from texastoast.arcade import ArcadeGame, GameInfo
from texastoast.core.tui_game import TuiGame, TuiInput
from texastoast.scene import SceneStack


class TuiHost:
    """Owns a terminal, a renderer and a stack of scenes.

    Satisfies :class:`texastoast.arcade.Host` structurally.
    """

    def __init__(self, title: str = "texastoast", fps: int = 20,
                 hold_ms: int = 0, **game_kwargs: Any):
        self._game = TuiGame(title=title, fps=fps,
                             input_source=TuiInput(hold_ms=hold_ms),
                             **game_kwargs)
        self._stack = SceneStack()
        self._game.set_update(self._update)
        self._game.set_render(self._stack.render)

    # ── Construction ────────────────────────────────────────────────

    @classmethod
    def for_game(cls, game: ArcadeGame, **game_kwargs: Any) -> TuiHost:
        """A host sized to one game, with that game already seated.

        What a game's own ``__main__`` wants: the terminal is built from the
        game's own declaration rather than from defaults it would then have to
        correct.
        """
        info = game.info
        host = cls(title=info.title, fps=info.fps, hold_ms=info.hold_ms,
                   **game_kwargs)
        host.seat(game)
        return host

    # ── Host protocol ───────────────────────────────────────────────

    @property
    def renderer(self):
        return self._game.renderer

    @property
    def input(self):
        return self._game.input

    def push_scene(self, scene: Any) -> None:
        self._stack.push(scene)

    def pop_scene(self) -> None:
        """Remove the top scene. Popping the last one ends the session.

        This is the call a game makes to say "I am done, take me back to
        wherever I came from", and only the host knows where that is. Run on
        its own, a game is the bottom of the stack and there is nowhere to go
        but out; seated by a launcher, the menu is underneath and the same call
        returns to it. One behaviour, both outcomes right, and the game needs
        no flag telling it which situation it is in.

        Quitting rather than refusing also handles the empty-stack problem it
        would otherwise create: a host with no scenes renders nothing and
        accepts no keys, which is indistinguishable from a hang. There is never
        an empty stack because the session ends first.
        """
        if len(self._stack) > 1:
            self._stack.pop()
        else:
            self.quit()

    def quit(self) -> None:
        self._game.quit()

    # ── Seating ─────────────────────────────────────────────────────

    def seat(self, game: ArcadeGame) -> Any:
        """Start ``game`` and push its scene. Returns the scene.

        The game's declared frame rate and input behaviour are applied here,
        not at construction: a launcher's menu may idle at 20 fps with edge
        input and hand over to something wanting 30 and held keys, and the
        game should not have to know it was seated rather than launched.
        """
        self.apply(game.info)
        scene = game.start(self)
        self.push_scene(scene)
        return scene

    def apply(self, info: GameInfo) -> None:
        """Retune the terminal to what ``info`` asks for."""
        if self._game.loop is not None:
            self._game.loop.target_fps = info.fps
        source = self._game.input
        if hasattr(source, "hold_ms"):
            source.hold_ms = info.hold_ms

    # ── Frame ───────────────────────────────────────────────────────

    def _update(self, dt: float) -> None:
        """Route keys to the top scene, then update the stack.

        Keys are drained here rather than bound individually because a terminal
        delivers them as a stream and the stack decides who gets them:
        ``dispatch_key`` reaches the top scene only, which is the same modality
        rule that governs updates.
        """
        for key in self._game.input.drain():
            self._stack.dispatch_key(key)
        self._stack.update(dt)

    def run(self) -> None:
        """Run until the game quits. Blocks."""
        self._game.start()

    # ── Introspection ───────────────────────────────────────────────

    @property
    def game(self) -> TuiGame:
        """The underlying terminal app. For tests and for a game that needs
        something this protocol deliberately does not expose."""
        return self._game

    @property
    def stack(self) -> SceneStack:
        return self._stack

    @property
    def scene(self):
        return self._stack.top


__all__ = ["TuiHost"]
