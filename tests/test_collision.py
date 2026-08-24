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


def test_tile_collision_wall_snaps_flush():
    grid = [
        [1, 1],
        [0, 0],
    ]
    tm = TileMap(grid, tile_size=16, solid_tiles={1})
    # Moving right into the wall at column 1: stop flush against its left face
    # (x=8 puts the box's right edge on the boundary), not back at the start.
    x, y = check_tile_collision(0, 0, 8, 8, tm, velocity_x=20.0, velocity_y=0)
    assert x == 8


def _corridor():
    """One row, 8 tiles wide, solid tile at column 3 (x 48..64)."""
    return TileMap([[0, 0, 0, 1, 0, 0, 0, 0]], tile_size=16, solid_tiles={1})


def test_tile_collision_no_tunneling():
    # A step far larger than a tile must not pass through the wall.
    tm = _corridor()
    x, _ = check_tile_collision(0, 0, 8, 8, tm, velocity_x=100.0)
    assert x == 40  # flush against the left face of column 3


def test_tile_collision_flush_from_the_right():
    tm = _corridor()
    x, _ = check_tile_collision(80, 0, 8, 8, tm, velocity_x=-100.0)
    assert x == 64  # flush against the right face of column 3


def test_tile_collision_flush_is_idempotent():
    tm = _corridor()
    # Already flush: pushing further into the wall changes nothing.
    assert check_tile_collision(40, 0, 8, 8, tm, velocity_x=5.0)[0] == 40
    assert check_tile_collision(64, 0, 8, 8, tm, velocity_x=-5.0)[0] == 64


def test_tile_collision_partial_step_still_moves():
    tm = _corridor()
    # Short of the wall, movement is unobstructed.
    assert check_tile_collision(0, 0, 8, 8, tm, velocity_x=4.0)[0] == 4.0


def test_tile_collision_vertical_down():
    tm = TileMap([[0], [0], [0], [1], [0], [0]], tile_size=16, solid_tiles={1})
    _, y = check_tile_collision(0, 0, 8, 8, tm, velocity_y=100.0)
    assert y == 40


def test_tile_collision_vertical_up():
    tm = TileMap([[0], [0], [0], [1], [0], [0]], tile_size=16, solid_tiles={1})
    _, y = check_tile_collision(0, 80, 8, 8, tm, velocity_y=-100.0)
    assert y == 64


def test_tile_collision_slides_along_wall():
    # Blocked horizontally, but vertical movement still goes through.
    tm = TileMap([[0, 1], [0, 0]], tile_size=16, solid_tiles={1})
    x, y = check_tile_collision(0, 0, 8, 8, tm, velocity_x=20.0, velocity_y=4.0)
    assert x == 8
    assert y == 4.0


def test_tile_collision_out_of_bounds_blocks():
    tm = TileMap([[0, 0]], tile_size=16, solid_tiles=set())
    assert check_tile_collision(0, 0, 8, 8, tm, velocity_x=-5.0)[0] == 0


def test_tile_collision_zero_tile_size_does_not_crash():
    tm = TileMap([[0, 0]], tile_size=0, solid_tiles={1})
    assert check_tile_collision(0, 0, 8, 8, tm, velocity_x=5.0) == (5.0, 0)
