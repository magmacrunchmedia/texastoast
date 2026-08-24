import math

import pytest

from texastoast.world.entity import Entity
from texastoast.world.tilemap import TileMap


def test_entity_defaults():
    e = Entity()
    assert e.x == 0
    assert e.y == 0
    assert e.width == 16
    assert e.height == 16


def test_entity_center():
    e = Entity(x=10, y=20, width=8, height=6)
    assert e.center_x == 14.0
    assert e.center_y == 23.0


def test_entity_move_no_tilemap():
    # speed is px/second, so one full second of dt covers exactly `speed` px.
    e = Entity(x=0, y=0, speed=10)
    e.move(1, 0, 1.0)
    assert e.x == 10.0
    assert e.y == 0


def test_entity_move_scales_with_dt():
    e = Entity(x=0, y=0, speed=100)
    e.move(1, 0, 0.5)
    assert e.x == 50.0


def test_entity_move_is_frame_rate_independent():
    slow = Entity(x=0, y=0, speed=100)
    fast = Entity(x=0, y=0, speed=100)
    for _ in range(30):
        slow.move(1, 0, 1 / 30)
    for _ in range(60):
        fast.move(1, 0, 1 / 60)
    assert slow.x == pytest.approx(fast.x)
    assert slow.x == pytest.approx(100.0)


def test_entity_diagonal_is_normalized():
    straight = Entity(speed=100)
    straight.move(1, 0, 1.0)
    diagonal = Entity(speed=100)
    diagonal.move(1, 1, 1.0)
    travelled = math.hypot(diagonal.x, diagonal.y)
    assert travelled == pytest.approx(straight.x)


def test_entity_sub_unit_direction_is_not_scaled_up():
    # A half-pressed analog direction should stay half speed, not be normalized
    # up to full speed.
    e = Entity(speed=100)
    e.move(0.5, 0, 1.0)
    assert e.x == pytest.approx(50.0)


def test_entity_velocity_is_per_second():
    e = Entity(speed=100)
    e.move(1, 0, 1 / 60)
    assert e.vel_x == pytest.approx(100.0)
    assert e.vel_y == 0.0


def test_entity_move_with_tilemap():
    grid = [
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ]
    tm = TileMap(grid, tile_size=16, solid_tiles={1})
    e = Entity(x=24, y=24, width=8, height=8, speed=10)
    e.move(1, 0, 1.0, tm)
    # Should move right (tile at 2,1 is 0 = not solid)
    assert e.x > 24


def test_entity_collides_with():
    a = Entity(x=0, y=0, width=10, height=10)
    b = Entity(x=5, y=5, width=10, height=10)
    c = Entity(x=20, y=20, width=10, height=10)
    assert a.collides_with(b) is True
    assert a.collides_with(c) is False
