from __future__ import annotations

from dataclasses import dataclass


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


def check_tile_collision(
    x: float, y: float, w: float, h: float, tilemap, velocity_x: float = 0, velocity_y: float = 0
) -> tuple[float, float]:
    """Resolve collision between a bounding box and solid tiles.
    Returns corrected (x, y) position."""
    ts = tilemap.tile_size
    corrected_x = x
    corrected_y = y

    next_x = x + velocity_x
    next_y = y + velocity_y

    # Check horizontal movement
    if velocity_x != 0:
        col = int((next_x + w - 1) // ts) if velocity_x > 0 else int(next_x // ts)
        start_row = int(y // ts)
        end_row = int((y + h - 1) // ts)
        blocked = False
        for row in range(start_row, end_row + 1):
            if tilemap.is_solid(col, row):
                blocked = True
                break
        if blocked:
            corrected_x = x
        else:
            corrected_x = next_x

    # Check vertical movement
    if velocity_y != 0:
        row = int((next_y + h - 1) // ts) if velocity_y > 0 else int(next_y // ts)
        start_col = int(corrected_x // ts)
        end_col = int((corrected_x + w - 1) // ts)
        blocked = False
        for col in range(start_col, end_col + 1):
            if tilemap.is_solid(col, row):
                blocked = True
                break
        if blocked:
            corrected_y = y
        else:
            corrected_y = next_y

    return corrected_x, corrected_y
