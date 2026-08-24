from __future__ import annotations

import math
from dataclasses import dataclass

# Boxes are half-open: a box at x with width w covers [x, x + w). A box whose
# right edge lands exactly on a tile boundary does not occupy the tile beyond
# it, which is what makes flush contact stable.
_EPS = 1e-9

# Safety valve for absurd velocities. Movement is split into sub-steps of at
# most one tile so nothing can pass through a wall; past this many sub-steps we
# stop subdividing, and tunneling becomes possible again.
MAX_SUBSTEPS = 256


@dataclass
class AABB:
    x: float
    y: float
    width: float
    height: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def intersects(self, other: AABB) -> bool:
        return not (self.right <= other.left or self.left >= other.right or
                    self.bottom <= other.top or self.top >= other.bottom)

    def contains_point(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.top <= py <= self.bottom


def _tile_span(lo: float, hi: float, tile_size: int) -> tuple[int, int]:
    """Inclusive range of tile indices covered by the half-open span [lo, hi)."""
    first = int(math.floor(lo / tile_size))
    last = int(math.floor((hi - _EPS) / tile_size))
    return first, max(first, last)


def _substeps(velocity_x: float, velocity_y: float, tile_size: int) -> int:
    """Number of sub-steps needed to keep each step within one tile."""
    longest = max(abs(velocity_x), abs(velocity_y))
    if longest <= tile_size:
        return 1
    return min(MAX_SUBSTEPS, int(math.ceil(longest / tile_size)))


def _resolve_x(x: float, y: float, w: float, h: float, tilemap, dx: float) -> float:
    ts = tilemap.tile_size
    next_x = x + dx
    if dx > 0:
        col = _tile_span(next_x, next_x + w, ts)[1]
    else:
        col = _tile_span(next_x, next_x + w, ts)[0]

    first_row, last_row = _tile_span(y, y + h, ts)
    for row in range(first_row, last_row + 1):
        if tilemap.is_solid(col, row):
            if dx > 0:
                flush = col * ts - w
                return flush if flush > x else x
            flush = (col + 1) * ts
            return flush if flush < x else x
    return next_x


def _resolve_y(x: float, y: float, w: float, h: float, tilemap, dy: float) -> float:
    ts = tilemap.tile_size
    next_y = y + dy
    if dy > 0:
        row = _tile_span(next_y, next_y + h, ts)[1]
    else:
        row = _tile_span(next_y, next_y + h, ts)[0]

    first_col, last_col = _tile_span(x, x + w, ts)
    for col in range(first_col, last_col + 1):
        if tilemap.is_solid(col, row):
            if dy > 0:
                flush = row * ts - h
                return flush if flush > y else y
            flush = (row + 1) * ts
            return flush if flush < y else y
    return next_y


def check_tile_collision(
    x: float, y: float, w: float, h: float, tilemap,
    velocity_x: float = 0.0, velocity_y: float = 0.0,
) -> tuple[float, float]:
    """Resolve movement of a box against a tile map's solid tiles.

    ``velocity_x``/``velocity_y`` are a displacement for this frame, not a rate.

    Each axis is resolved independently so an entity slides along a wall
    instead of sticking to it. A blocked axis snaps flush against the wall face
    rather than reverting to its starting position, and movement is split into
    sub-steps of at most one tile so a fast-moving box cannot pass through a
    wall (up to ``MAX_SUBSTEPS``).

    Returns the corrected ``(x, y)`` position.
    """
    ts = tilemap.tile_size
    if ts <= 0:
        return x + velocity_x, y + velocity_y

    steps = _substeps(velocity_x, velocity_y, ts)
    step_x = velocity_x / steps
    step_y = velocity_y / steps

    for _ in range(steps):
        if step_x:
            x = _resolve_x(x, y, w, h, tilemap, step_x)
        if step_y:
            y = _resolve_y(x, y, w, h, tilemap, step_y)

    return x, y
