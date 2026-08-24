"""Tile editor tests. The editor lives in tools/ rather than the package, so
it is loaded by path."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from conftest import requires_tk

from texastoast.world.tilemap import TileMap

pytestmark = requires_tk

_EDITOR_PATH = Path(__file__).resolve().parent.parent / "tools" / "tile_editor.py"


@pytest.fixture(scope="module")
def editor_module():
    spec = importlib.util.spec_from_file_location("tile_editor", _EDITOR_PATH)
    module = importlib.util.module_from_spec(spec)
    # dataclass resolves string annotations through sys.modules.
    sys.modules["tile_editor"] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop("tile_editor", None)


@pytest.fixture
def editor(editor_module, tk_root):
    return editor_module.TileEditor(tk_root)


def test_only_tiles_marked_solid_are_saved(editor, tmp_path):
    # Regression: solid_tiles was "every non-zero id in the grid", so grass,
    # paths, NPCs and signs all became walls the player could not walk on.
    editor._grid = [[0, 1, 3], [6, 0, 1], [0, 0, 0]]
    editor._rows, editor._cols = 3, 3

    path = tmp_path / "map.json"
    editor._do_save(str(path))

    assert json.loads(path.read_text())["solid_tiles"] == [1]

    tm = TileMap.from_file(path)
    assert tm.is_solid(1, 0) is True    # wall
    assert tm.is_solid(2, 0) is False   # path
    assert tm.is_solid(0, 1) is False   # npc
    assert tm.is_solid(0, 0) is False   # grass


def test_toggling_solid_changes_what_is_saved(editor, tmp_path):
    editor._grid = [[3]]
    editor._rows = editor._cols = 1

    editor._solid_vars[3].set(True)
    editor._toggle_solid(3)

    path = tmp_path / "map.json"
    editor._do_save(str(path))
    assert json.loads(path.read_text())["solid_tiles"] == [3]


def test_unused_tiles_are_not_saved_as_solid(editor, tmp_path):
    # Water is solid in the palette but absent from this map.
    editor._grid = [[0, 1]]
    editor._rows, editor._cols = 1, 2
    path = tmp_path / "map.json"
    editor._do_save(str(path))
    assert json.loads(path.read_text())["solid_tiles"] == [1]


def test_open_restores_solid_flags(editor, editor_module, tmp_path, monkeypatch):
    path = tmp_path / "map.json"
    path.write_text(json.dumps({
        "grid": [[0, 5], [5, 0]],
        "tile_size": 16,
        "solid_tiles": [5],
    }))
    monkeypatch.setattr(editor_module.filedialog, "askopenfilename",
                        lambda **kw: str(path))
    editor._open_file()

    assert editor._palette[5].solid is True
    assert editor._palette[1].solid is False  # wall is not solid in this map


def test_open_pads_ragged_rows(editor, editor_module, tmp_path, monkeypatch):
    # A short row used to leave _cols wider than the row, so painting there
    # raised IndexError.
    path = tmp_path / "ragged.json"
    path.write_text(json.dumps({
        "grid": [[0, 1, 2], [3], [4, 5]],
        "tile_size": 16,
        "solid_tiles": [1],
    }))
    monkeypatch.setattr(editor_module.filedialog, "askopenfilename",
                        lambda **kw: str(path))
    editor._open_file()

    assert editor._cols == 3
    assert editor._grid == [[0, 1, 2], [3, 0, 0], [4, 5, 0]]
    assert all(len(row) == editor._cols for row in editor._grid)


def test_open_rejects_a_grid_that_is_not_rows(editor, editor_module, tmp_path, monkeypatch):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"grid": "not a grid"}))
    monkeypatch.setattr(editor_module.filedialog, "askopenfilename",
                        lambda **kw: str(path))
    errors = []
    monkeypatch.setattr(editor_module.messagebox, "showerror",
                        lambda title, msg: errors.append(msg))
    editor._open_file()
    assert errors  # reported to the user, not raised


def test_undo_redo_round_trip(editor):
    editor._grid = [[0, 0], [0, 0]]
    editor._rows = editor._cols = 2
    editor._push_history()
    editor._grid[0][0] = 1

    editor._undo()
    assert editor._grid[0][0] == 0
    editor._redo()
    assert editor._grid[0][0] == 1
