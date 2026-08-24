from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    title: str = "texastoast"
    width: int = 640
    height: int = 480
    fps: int = 30
    tile_size: int = 16
    bg_color: str = "#1a1a2e"
    grid_color: str = "#16213e"
    debug: bool = False


DEFAULT_CONFIG = Config()
