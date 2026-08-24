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
