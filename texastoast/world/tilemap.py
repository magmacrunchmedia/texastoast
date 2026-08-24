from __future__ import annotations

import json
from pathlib import Path


class TileMap:
    """2D tile grid with collision data."""

    def __init__(
        self,
        grid: list[list[int]],
        tile_size: int = 16,
        solid_tiles: set[int] | None = None,
    ):
        self._grid = grid
        self._tile_size = tile_size
        self._solid_tiles = solid_tiles if solid_tiles is not None else set()

    @classmethod
    def from_file(cls, path: str | Path, tile_size: int | None = None, solid_tiles: set[int] | None = None) -> TileMap:
        with open(path) as f:
            data = json.load(f)
        ts = tile_size if tile_size is not None else data.get("tile_size", 16)
        st = solid_tiles if solid_tiles is not None else set(data.get("solid_tiles", []))
        return cls(data["grid"], tile_size=ts, solid_tiles=st)

    @property
    def grid(self) -> list[list[int]]:
        return self._grid

    @property
    def tile_size(self) -> int:
        return self._tile_size

    @property
    def rows(self) -> int:
        return len(self._grid)

    @property
    def cols(self) -> int:
        if not self._grid:
            return 0
        return max(len(row) for row in self._grid)

    @property
    def width(self) -> int:
        return self.cols * self._tile_size

    @property
    def height(self) -> int:
        return self.rows * self._tile_size

    def get(self, col: int, row: int) -> int:
        if 0 <= row < self.rows and 0 <= col < len(self._grid[row]):
            return self._grid[row][col]
        return -1

    def set(self, col: int, row: int, tile_id: int):
        if 0 <= row < self.rows and 0 <= col < len(self._grid[row]):
            self._grid[row][col] = tile_id

    def is_solid(self, col: int, row: int) -> bool:
        tile_id = self.get(col, row)
        if tile_id == -1:
            return True
        return tile_id in self._solid_tiles

    def is_solid_at(self, world_x: float, world_y: float) -> bool:
        col = int(world_x // self._tile_size)
        row = int(world_y // self._tile_size)
        return self.is_solid(col, row)

    def to_grid_coords(self, world_x: float, world_y: float) -> tuple[int, int]:
        return int(world_x // self._tile_size), int(world_y // self._tile_size)

    def save(self, path: str | Path, solid_tiles: set[int] | None = None):
        data = {
            "grid": self._grid,
            "tile_size": self._tile_size,
            "solid_tiles": list(solid_tiles if solid_tiles is not None else self._solid_tiles),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
