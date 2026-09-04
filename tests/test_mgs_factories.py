"""magmascript domain factory tests for the 0.5.0 additions — headless."""
import pytest

from texastoast.audio.mixer import Mixer
from texastoast.input.players import PlayerManager
from texastoast.mgs import TexastoastDomain
from texastoast.scene import SceneStack
from texastoast.ui.theme import DEFAULT_THEME, Theme
from texastoast.world.group import EntityGroup

tt = TexastoastDomain()


def test_scenes_factory():
    assert isinstance(tt.scenes(), SceneStack)


def test_entities_factory():
    assert isinstance(tt.entities(), EntityGroup)


def test_sprite_sheet_factory():
    # The one factory here backed by tkinter, so its import is local — the
    # module docstring's "headless" only holds if the rest still collects
    # where tkinter is absent.
    SpriteSheet = pytest.importorskip(
        "texastoast.render.sprite", reason="tkinter is not installed"
    ).SpriteSheet

    sheet = tt.sprite_sheet("sheet.png", 16, 16)
    assert isinstance(sheet, SpriteSheet)


def test_theme_factory_defaults():
    theme = tt.theme()
    assert theme == DEFAULT_THEME


def test_theme_factory_overrides():
    theme = tt.theme({"primary": "#4fc3f7"})
    assert isinstance(theme, Theme)
    assert theme.primary == "#4fc3f7"
    assert theme.text == DEFAULT_THEME.text


def test_theme_factory_rejects_unknown_key():
    with pytest.raises(ValueError, match="primary"):
        tt.theme({"primry": "#fff"})   # typo — error names the valid keys


def test_players_factory():
    manager = tt.players({"max_players": 2, "join_buttons": ["start"]})
    assert isinstance(manager, PlayerManager)
    assert len(manager.players) == 2


def test_players_factory_rejects_unknown_key():
    with pytest.raises(ValueError, match="max_players"):
        tt.players({"players": 2})


def test_mixer_factory_never_raises():
    mixer = tt.mixer()
    assert isinstance(mixer, Mixer)
    mixer.close()


def test_ui_factories_accept_theme():
    # Headless: a fake surface stands in for the renderer.
    class FakeSurface:
        width, height = 640, 480

        def begin_group(self, g): ...
        def clear_group(self, g): ...
        def ui_rect(self, *a, **k): ...
        def ui_text(self, *a, **k): ...

    custom = tt.theme({"primary": "#123456"})
    menu = tt.menu(FakeSurface(), {"theme": custom})
    assert menu._selected_color == "#123456"
