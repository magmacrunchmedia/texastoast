"""TuiHost — the concrete terminal host.

The half of a game's wiring that is not any particular game's business. These
cover the two things that make it worth sharing: that it satisfies the arcade
Host protocol, and that seating a game applies that game's declared frame rate
and input behaviour rather than the host's own.
"""

import pytest

pytest.importorskip("textual", reason='needs the tui extra: pip install "texastoast[tui]"')

from texastoast.arcade import ArcadeGame, GameInfo, Host  # noqa: E402
from texastoast.core.tui_host import TuiHost  # noqa: E402


class Scene:
    def __init__(self, name="scene"):
        self.name = name
        self.updates = 0
        self.renders = 0
        self.keys = []

    def update(self, dt):
        self.updates += 1

    def render(self):
        self.renders += 1

    def handle_key(self, key):
        self.keys.append(key)
        return True


class Game:
    """A minimal ArcadeGame."""

    def __init__(self, info=None, scene=None):
        self.info = info or GameInfo(key="demo", title="Demo", blurb="b")
        self.scene = scene or Scene()
        self.host = None

    def start(self, host):
        self.host = host
        return self.scene


@pytest.fixture
def host():
    return TuiHost(title="test", fps=20, hold_ms=0)


# ── The protocol ────────────────────────────────────────────────────


def test_a_host_satisfies_the_arcade_host_protocol(host):
    assert isinstance(host, Host)


def test_a_host_exposes_a_renderer_and_an_input_source(host):
    from texastoast.render.abstract import Renderer, UISurface

    assert isinstance(host.renderer, Renderer)
    assert isinstance(host.renderer, UISurface)
    assert hasattr(host.input, "poll")
    assert hasattr(host.input, "drain")


# ── Scenes ──────────────────────────────────────────────────────────


def test_pushing_and_popping_moves_the_top_scene(host):
    a, b = Scene("a"), Scene("b")
    host.push_scene(a)
    host.stack.update(0)
    assert host.scene is a

    host.push_scene(b)
    host.stack.update(0)
    assert host.scene is b

    host.pop_scene()
    host.stack.update(0)
    assert host.scene is a


def test_popping_the_last_scene_ends_the_session(host):
    # The call a game makes to say "take me back to wherever I came from".
    # Standalone there is nowhere to go but out; the alternative — refusing —
    # leaves a game's own menu with no way to exit.
    quit_calls = []
    host.quit = lambda: quit_calls.append(1)

    host.push_scene(Scene())
    host.stack.update(0)
    host.pop_scene()

    assert quit_calls == [1]


def test_popping_with_something_underneath_goes_back_instead_of_quitting(host):
    quit_calls = []
    host.quit = lambda: quit_calls.append(1)
    under, over = Scene("under"), Scene("over")
    host.push_scene(under)
    host.push_scene(over)
    host.stack.update(0)

    host.pop_scene()
    host.stack.update(0)

    assert host.scene is under
    assert quit_calls == []


def test_the_stack_is_never_left_empty(host):
    # Whatever happens, there is always either a scene or no session — never a
    # host rendering nothing and accepting no keys, which looks like a hang.
    host.push_scene(Scene())
    host.stack.update(0)
    host.pop_scene()
    host.stack.update(0)
    assert len(host.stack) >= 1


def test_keys_reach_the_top_scene_only(host):
    under, over = Scene("under"), Scene("over")
    host.push_scene(under)
    host.push_scene(over)
    host.stack.update(0)

    host.input.press("x")
    host._update(0.05)

    assert over.keys == ["x"]
    assert under.keys == []


def test_the_frame_drains_input_then_updates(host):
    scene = Scene()
    host.push_scene(scene)
    host.stack.update(0)

    host.input.press("a")
    host.input.press("b")
    host._update(0.05)

    assert scene.keys == ["a", "b"]
    assert scene.updates >= 1
    # Drained, so a second frame sees nothing new.
    host._update(0.05)
    assert scene.keys == ["a", "b"]


# ── Seating ─────────────────────────────────────────────────────────


def test_seating_a_game_starts_it_and_pushes_its_scene(host):
    game = Game()
    scene = host.seat(game)
    host.stack.update(0)

    assert game.host is host
    assert scene is game.scene
    assert host.scene is game.scene


def test_seating_applies_the_games_declared_input_behaviour(host):
    # The whole reason hold_ms is in GameInfo: a menu idling with edge input
    # hands over to a real-time game that needs held keys.
    assert host.input.hold_ms == 0
    host.seat(Game(GameInfo(key="rt", title="RT", blurb="b", hold_ms=140)))
    assert host.input.hold_ms == 140


def test_seating_before_the_loop_exists_does_not_raise(host):
    # for_game() passes the rate to the constructor, so a host built that way
    # has no loop to retune at seating time. apply() has to tolerate that.
    assert host.game.loop is None
    game = Game(GameInfo(key="rt", title="RT", blurb="b", fps=30))
    host.seat(game)
    host.stack.update(0)
    assert host.scene is game.scene


def test_seating_retunes_a_running_loop():
    from texastoast.core.loop import GameLoop
    from texastoast.core.scheduler import ManualScheduler

    host = TuiHost(title="t", fps=20)
    host._game._loop = GameLoop(ManualScheduler(), lambda dt: None,
                                lambda: None, fps=20)
    assert round(host.game.loop.target_fps) == 20

    host.seat(Game(GameInfo(key="rt", title="RT", blurb="b", fps=30)))
    assert round(host.game.loop.target_fps) == 30


def test_for_game_builds_a_host_sized_to_that_game():
    game = Game(GameInfo(key="rt", title="Real Time", blurb="b",
                         fps=30, hold_ms=120))
    host = TuiHost.for_game(game)
    host.stack.update(0)

    assert host.game.config.title == "Real Time"
    assert host.input.hold_ms == 120
    assert host.scene is game.scene
    assert game.host is host


def test_a_second_game_can_be_seated_over_the_first(host):
    # What a launcher does: the menu stays underneath and Esc returns to it.
    menu = Scene("menu")
    host.push_scene(menu)
    game = Game()
    host.seat(game)
    host.stack.update(0)
    assert host.scene is game.scene

    host.pop_scene()
    host.stack.update(0)
    assert host.scene is menu


def test_the_demo_game_is_a_valid_arcade_game():
    assert isinstance(Game(), ArcadeGame)
