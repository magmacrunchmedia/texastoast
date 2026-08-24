from __future__ import annotations

from texastoast.world.collision import AABB


class Entity:
    """Base game entity with position, velocity, and hitbox."""

    def __init__(
        self,
        x: float = 0,
        y: float = 0,
        width: float = 16,
        height: float = 16,
        speed: float = 1.0,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.speed = speed
        self.vel_x = 0.0
        self.vel_y = 0.0

    @property
    def aabb(self) -> AABB:
        return AABB(self.x, self.y, self.width, self.height)

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def move(self, dx: float, dy: float, tilemap=None):
        from texastoast.world.collision import check_tile_collision

        self.vel_x = dx * self.speed
        self.vel_y = dy * self.speed

        if tilemap:
            self.x, self.y = check_tile_collision(
                self.x, self.y, self.width, self.height,
                tilemap, self.vel_x, self.vel_y,
            )
        else:
            self.x += self.vel_x
            self.y += self.vel_y

    def update(self, dt: float):
        pass

    def collides_with(self, other: Entity) -> bool:
        return self.aabb.intersects(other.aabb)
