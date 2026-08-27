"""The arcade seam.

The contract a launcher and a game agree on without either importing the other.
Everything here runs with no terminal library installed, because the protocol
deliberately depends on nothing — that independence is most of the point.
"""

import warnings
from dataclasses import FrozenInstanceError

import pytest

from texastoast.arcade import (
    ENTRY_POINT_GROUP,
    ArcadeGame,
    GameInfo,
    Host,
    discover,
)


def info(**overrides) -> GameInfo:
    base = {"key": "demo", "title": "Demo", "blurb": "a demo"}
    return GameInfo(**{**base, **overrides})


class FakeGame:
    def __init__(self, game_info=None):
        self.info = game_info or info()
        self.started_with = None

    def start(self, host):
        self.started_with = host
        return object()


class FakeHost:
    renderer = object()
    input = object()

    def __init__(self):
        self.pushed = []
        self.popped = 0
        self.quit_called = False

    def push_scene(self, scene):
        self.pushed.append(scene)

    def pop_scene(self):
        self.popped += 1

    def quit(self):
        self.quit_called = True


# ── GameInfo ────────────────────────────────────────────────────────


def test_a_game_only_has_to_state_three_things():
    i = GameInfo(key="x", title="X", blurb="b")
    assert (i.fps, i.hold_ms) == (20, 0)
    assert (i.min_cols, i.min_rows) == (60, 20)


def test_edge_input_is_the_default_because_most_games_are_turn_based():
    # hold_ms=0 means one keystroke, one action. A decay timer would turn a
    # single arrow press into a slide, since terminals repeat but never release.
    assert GameInfo(key="x", title="X", blurb="b").hold_ms == 0


def test_a_real_time_game_says_so():
    i = info(fps=30, hold_ms=120)
    assert i.fps == 30
    assert i.hold_ms == 120


def test_fits_reports_whether_a_terminal_is_big_enough():
    i = info(min_cols=58, min_rows=22)
    assert i.fits(80, 24)
    assert i.fits(58, 22)
    assert not i.fits(57, 22)
    assert not i.fits(58, 21)


def test_game_info_is_frozen():
    # A launcher reads it repeatedly and must not be able to edit a game's
    # declaration by accident.
    with pytest.raises(FrozenInstanceError):
        info().key = "changed"


# ── The protocols ───────────────────────────────────────────────────


def test_an_object_with_info_and_start_is_an_arcade_game():
    assert isinstance(FakeGame(), ArcadeGame)


@pytest.mark.parametrize(
    "cls",
    [
        type("NoStart", (), {"info": info()}),
        type("NoInfo", (), {"start": lambda self, host: None}),
        type("Neither", (), {}),
    ],
)
def test_a_partial_implementation_is_not_an_arcade_game(cls):
    assert not isinstance(cls(), ArcadeGame)


def test_a_host_is_recognised_structurally():
    assert isinstance(FakeHost(), Host)


def test_something_missing_a_host_method_is_not_a_host():
    class Partial:
        renderer = None
        input = None

        def push_scene(self, scene):
            pass

    assert not isinstance(Partial(), Host)


def test_start_receives_the_host_and_returns_a_scene_without_pushing_it():
    # The caller pushes. A game that pushed its own scene would take the
    # decision away from whatever is seating it.
    game, host = FakeGame(), FakeHost()
    scene = game.start(host)
    assert game.started_with is host
    assert scene is not None
    assert host.pushed == []


# ── Discovery ───────────────────────────────────────────────────────


class FakeEntryPoint:
    def __init__(self, name, value):
        self.name = name
        self._value = value

    def load(self):
        if isinstance(self._value, Exception):
            raise self._value
        return self._value


def patch_entry_points(monkeypatch, entries):
    def fake(group=None):
        assert group == ENTRY_POINT_GROUP
        return entries

    monkeypatch.setattr("importlib.metadata.entry_points", fake)


def test_discover_returns_installed_games_sorted_by_title(monkeypatch):
    zed = FakeGame(info(key="z", title="Zebra", blurb="z"))
    ant = FakeGame(info(key="a", title="Ant", blurb="a"))
    patch_entry_points(monkeypatch, [FakeEntryPoint("z", zed), FakeEntryPoint("a", ant)])

    found = discover()
    assert [g.info.title for g in found] == ["Ant", "Zebra"]


def test_discover_finds_nothing_when_nothing_is_installed(monkeypatch):
    patch_entry_points(monkeypatch, [])
    assert discover() == []


def test_one_broken_game_does_not_take_the_arcade_down(monkeypatch):
    # A machine with a half-installed game should lose that game, not the menu.
    good = FakeGame(info(title="Good"))
    patch_entry_points(monkeypatch, [
        FakeEntryPoint("broken", ImportError("no such module")),
        FakeEntryPoint("good", good),
    ])

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        found = discover()

    assert [g.info.title for g in found] == ["Good"]
    assert any("broken" in str(w.message) for w in caught)


def test_a_failure_is_warned_about_rather_than_swallowed(monkeypatch):
    patch_entry_points(monkeypatch, [FakeEntryPoint("bad", RuntimeError("boom"))])
    with pytest.warns(RuntimeWarning, match="could not load arcade game 'bad'"):
        assert discover() == []


def test_an_entry_point_that_is_not_a_game_is_rejected_with_a_reason(monkeypatch):
    patch_entry_points(monkeypatch, [FakeEntryPoint("wrong", object())])
    with pytest.warns(RuntimeWarning, match="does not satisfy ArcadeGame"):
        assert discover() == []


def test_the_entry_point_group_is_the_arcade_namespace():
    # Named for the arcade, not the engine: this module defines the shape of
    # what goes in the group, but the group belongs to the launcher.
    assert ENTRY_POINT_GROUP == "magmacrunch.games"


# ── Independence ────────────────────────────────────────────────────


def test_the_seam_depends_on_nothing():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; import texastoast.arcade as a; "
         "print(a.GameInfo(key='k', title='T', blurb='b').fps, "
         "'tkinter' in sys.modules, 'textual' in sys.modules)"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "20 False False"
