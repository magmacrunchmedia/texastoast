from texastoast.world.tilemap import TileMap


def test_tilemap_basic():
    grid = [
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1],
    ]
    tm = TileMap(grid, tile_size=16, solid_tiles={1})
    assert tm.rows == 3
    assert tm.cols == 3
    assert tm.width == 48
    assert tm.height == 48


def test_tilemap_get():
    grid = [[0, 1], [2, 3]]
    tm = TileMap(grid)
    assert tm.get(0, 0) == 0
    assert tm.get(1, 0) == 1
    assert tm.get(0, 1) == 2
    assert tm.get(1, 1) == 3


def test_tilemap_out_of_bounds():
    grid = [[0, 1]]
    tm = TileMap(grid)
    assert tm.get(-1, 0) == -1
    assert tm.get(0, -1) == -1
    assert tm.get(5, 0) == -1


def test_tilemap_solid():
    grid = [
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1],
    ]
    tm = TileMap(grid, solid_tiles={1})
    assert tm.is_solid(0, 0) is True
    assert tm.is_solid(1, 1) is False
    assert tm.is_solid(-1, 0) is True  # out of bounds = solid


def test_tilemap_solid_at():
    grid = [
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1],
    ]
    tm = TileMap(grid, tile_size=16, solid_tiles={1})
    assert tm.is_solid_at(24.0, 24.0) is False  # center tile (1,1)
    assert tm.is_solid_at(0.0, 0.0) is True  # corner tile (0,0)


def test_tilemap_set():
    grid = [[0, 0], [0, 0]]
    tm = TileMap(grid)
    tm.set(1, 1, 5)
    assert tm.get(1, 1) == 5


def test_tilemap_to_grid_coords():
    tm = TileMap([[0]], tile_size=16)
    assert tm.to_grid_coords(0.0, 0.0) == (0, 0)
    assert tm.to_grid_coords(16.0, 32.0) == (1, 2)
    assert tm.to_grid_coords(15.9, 15.9) == (0, 0)


def test_tilemap_jagged_grid():
    grid = [[0, 1, 2], [3, 4], [5]]
    tm = TileMap(grid)
    assert tm.rows == 3
    assert tm.cols == 3  # max width
    assert tm.get(0, 0) == 0
    assert tm.get(2, 0) == 2
    assert tm.get(0, 1) == 3
    assert tm.get(1, 1) == 4
    assert tm.get(2, 1) == -1  # row 1 only has 2 cols
    assert tm.get(0, 2) == 5
    assert tm.get(1, 2) == -1  # row 2 only has 1 col


def test_tilemap_empty_solid_tiles():
    tm = TileMap([[0, 0], [0, 0]], solid_tiles=set())
    assert tm.is_solid(0, 0) is False
    assert tm.is_solid(1, 1) is False


def test_tilemap_save_load_roundtrip(tmp_path):
    grid = [[0, 1, 2], [3, 4, 5]]
    tm = TileMap(grid, tile_size=32, solid_tiles={1, 2})
    path = tmp_path / "test.json"
    tm.save(path)
    loaded = TileMap.from_file(path)
    assert loaded.grid == grid
    assert loaded.tile_size == 32
    assert loaded._solid_tiles == {1, 2}


def test_tilemap_load_ignores_saved_tile_size_when_override(tmp_path):
    grid = [[0]]
    tm = TileMap(grid, tile_size=32)
    path = tmp_path / "test.json"
    tm.save(path)
    loaded = TileMap.from_file(path, tile_size=64)
    assert loaded.tile_size == 64


def test_tilemap_empty_grid():
    tm = TileMap([])
    assert tm.rows == 0
    assert tm.cols == 0
