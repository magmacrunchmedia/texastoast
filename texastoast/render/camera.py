from __future__ import annotations

import math
from dataclasses import dataclass

# ``smoothing`` was calibrated as a per-frame lerp factor at this rate, so it
# is the rate at which the old and new behaviour agree exactly.
REFERENCE_FPS = 30.0


@dataclass
class Camera:
    """Viewport camera with smooth following."""
    width: int = 640
    height: int = 480
    x: float = 0.0
    y: float = 0.0
    smoothing: float = 0.1

    def follow(self, target_x: float, target_y: float, map_width: int = 0,
               map_height: int = 0, dt: float | None = None):
        """Ease the viewport towards ``(target_x, target_y)``.

        Pass the frame's ``dt`` to make the easing frame-rate independent:
        ``smoothing`` is then a per-frame factor *at 30 fps*, converted to a
        time constant, so the camera lags by the same distance at any fps.
        Omitting ``dt`` keeps the old per-frame behaviour.
        """
        target_cx = target_x - self.width / 2
        target_cy = target_y - self.height / 2

        alpha = self._alpha(dt)
        self.x += (target_cx - self.x) * alpha
        self.y += (target_cy - self.y) * alpha

        if map_width > 0:
            self.x = max(0, min(self.x, map_width - self.width))
        if map_height > 0:
            self.y = max(0, min(self.y, map_height - self.height))

    def _alpha(self, dt: float | None) -> float:
        """The lerp factor for this frame.

        Applying ``smoothing`` once per frame means the camera converges twice
        as fast at 60 fps as at 30. Treating it as a per-second time constant
        and integrating over ``dt`` removes the dependency.
        """
        s = min(max(self.smoothing, 0.0), 1.0)
        if dt is None:
            return s
        if s >= 1.0:
            return 1.0
        if s <= 0.0 or dt <= 0.0:
            return 0.0
        rate = -math.log(1.0 - s) * REFERENCE_FPS
        return 1.0 - math.exp(-rate * dt)

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
