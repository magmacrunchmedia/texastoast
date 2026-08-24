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
    e = Entity(x=0, y=0, speed=10)
    e.move(1, 0)
    assert e.x == 10.0
    assert e.y == 0


def test_entity_move_with_tilemap():
    grid = [
        [1, 1, 1, 1],
        [1, 0, 0, 1],
        [1, 0, 0, 1],
        [1, 1, 1, 1],
    ]
    tm = TileMap(grid, tile_size=16, solid_tiles={1})
    e = Entity(x=24, y=24, width=8, height=8, speed=10)
    e.move(1, 0, tm)
    # Should move right (tile at 2,1 is 0 = not solid)
    assert e.x > 24


def test_entity_collides_with():
    a = Entity(x=0, y=0, width=10, height=10)
    b = Entity(x=5, y=5, width=10, height=10)
    c = Entity(x=20, y=20, width=10, height=10)
    assert a.collides_with(b) is True
    assert a.collides_with(c) is False
