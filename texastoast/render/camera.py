from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Camera:
    """Viewport camera with smooth following."""
    width: int = 640
    height: int = 480
    x: float = 0.0
    y: float = 0.0
    smoothing: float = 0.1

    def follow(self, target_x: float, target_y: float, map_width: int = 0, map_height: int = 0):
        target_cx = target_x - self.width / 2
        target_cy = target_y - self.height / 2

        self.x += (target_cx - self.x) * self.smoothing
        self.y += (target_cy - self.y) * self.smoothing

        if map_width > 0:
            self.x = max(0, min(self.x, map_width - self.width))
        if map_height > 0:
            self.y = max(0, min(self.y, map_height - self.height))

    def set_position(self, x: float, y: float):
        self.x = x
        self.y = y

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        return wx - self.x, wy - self.y

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return sx + self.x, sy + self.y

    def is_visible(self, x: float, y: float, w: float, h: float) -> bool:
        return not (x + w < self.x or x > self.x + self.width or
                    y + h < self.y or y > self.y + self.height)
