from texastoast.world.collision import AABB, check_tile_collision
from texastoast.world.tilemap import TileMap


def test_aabb_intersect():
    a = AABB(0, 0, 10, 10)
    b = AABB(5, 5, 10, 10)
    assert a.intersects(b) is True


def test_aabb_no_intersect():
    a = AABB(0, 0, 10, 10)
    b = AABB(20, 20, 10, 10)
    assert a.intersects(b) is False


def test_aabb_touching_edges():
    a = AABB(0, 0, 10, 10)
    b = AABB(10, 0, 10, 10)
    assert a.intersects(b) is False  # touching but not overlapping


def test_aabb_contains_point():
    a = AABB(0, 0, 10, 10)
    assert a.contains_point(5, 5) is True
    assert a.contains_point(0, 0) is True
    assert a.contains_point(10, 10) is True
    assert a.contains_point(11, 5) is False


def test_aabb_properties():
    a = AABB(5, 10, 20, 30)
    assert a.left == 5
    assert a.right == 25
    assert a.top == 10
    assert a.bottom == 40


def test_tile_collision_no_wall():
    grid = [[0, 0], [0, 0]]
    tm = TileMap(grid, tile_size=16, solid_tiles=set())
    x, y = check_tile_collision(0, 0, 8, 8, tm, velocity_x=1.0, velocity_y=0)
    assert x == 1.0
    assert y == 0


def test_tile_collision_wall():
    grid = [
        [1, 1],
        [0, 0],
    ]
    tm = TileMap(grid, tile_size=16, solid_tiles={1})
    # Moving right into a wall at column 1
    x, y = check_tile_collision(0, 0, 8, 8, tm, velocity_x=20.0, velocity_y=0)
    assert x == 0  # blocked
