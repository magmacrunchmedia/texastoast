from __future__ import annotations

import math

from texastoast.world.collision import AABB, check_tile_collision


class Entity:
    """Base game entity with position, velocity, and hitbox.

    ``speed`` is in pixels per second. :meth:`move` takes the frame's delta
    time, so movement is frame-rate independent.
    """

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
        # Set False to be culled by an EntityGroup after the next update pass —
        # lets an entity die inside its own update() without a group reference.
        self.alive = True

    @property
    def aabb(self) -> AABB:
        return AABB(self.x, self.y, self.width, self.height)

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def move(self, dx: float, dy: float, dt: float, tilemap=None):
        """Move along the direction vector ``(dx, dy)`` for ``dt`` seconds.

        ``dx``/``dy`` are direction components, normally -1, 0 or 1 (see
        :attr:`~texastoast.input.abstract.InputState.dx`). A diagonal is
        normalized, so moving on both axes is no faster than moving on one.

        Sets :attr:`vel_x`/:attr:`vel_y` to the resulting velocity in pixels
        per second. When ``tilemap`` is given, movement is resolved against its
        solid tiles.
        """
        magnitude = math.hypot(dx, dy)
        if magnitude > 1.0:
            dx /= magnitude
            dy /= magnitude

        self.vel_x = dx * self.speed
        self.vel_y = dy * self.speed

        step_x = self.vel_x * dt
        step_y = self.vel_y * dt

        if tilemap is not None:
            self.x, self.y = check_tile_collision(
                self.x, self.y, self.width, self.height,
                tilemap, step_x, step_y,
            )
        else:
            self.x += step_x
            self.y += step_y

    def update(self, dt: float):
        pass

    def collides_with(self, other: Entity) -> bool:
        return self.aabb.intersects(other.aabb)
