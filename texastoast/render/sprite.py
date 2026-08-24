from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Optional


class SpriteSheet:
    """Loads a sprite sheet PNG and extracts individual frames."""

    def __init__(self, path: str | Path, frame_width: int, frame_height: int):
        self._path = Path(path)
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._image: Optional[tk.PhotoImage] = None
        self._frames: dict[tuple[int, int], tk.PhotoImage] = {}

    def load(self, root) -> tk.PhotoImage:
        if self._image is None:
            self._image = tk.PhotoImage(file=str(self._path))
        return self._image

    def get_frame(self, root, col: int, row: int) -> tk.PhotoImage:
        key = (col, row)
        if key in self._frames:
            return self._frames[key]

        if self._image is None:
            self.load(root)

        x = col * self._frame_width
        y = row * self._frame_height
        frame = self._image.subsample(1, 1)  # full image
        # Use crop via PhotoImage if available, otherwise subsample
        self._frames[key] = frame
        return frame

    @property
    def frame_width(self) -> int:
        return self._frame_width

    @property
    def frame_height(self) -> int:
        return self._frame_height


def load_image(root, path: str | Path) -> tk.PhotoImage:
    return tk.PhotoImage(file=str(path))
