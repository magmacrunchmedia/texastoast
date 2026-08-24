from __future__ import annotations

import tkinter as tk
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class SpriteSheet:
    """Loads a sprite sheet PNG and extracts individual frames.

    Supports two backends:
    - PIL/Pillow (preferred) — proper pixel-accurate cropping
    - tkinter PhotoImage — fallback with copy() region extraction
    """

    def __init__(self, path: str | Path, frame_width: int, frame_height: int):
        self._path = Path(path)
        self._frame_width = frame_width
        self._frame_height = frame_height
        self._image: Optional[tk.PhotoImage] = None
        self._pil_image: Optional[object] = None
        self._frames: dict[tuple[int, int], tk.PhotoImage] = {}
        self._root = None

    def load(self, root) -> tk.PhotoImage:
        if self._image is not None:
            return self._image

        self._root = root

        if HAS_PIL:
            self._pil_image = Image.open(self._path)
            self._image = ImageTk.PhotoImage(self._pil_image)
        else:
            self._image = tk.PhotoImage(file=str(self._path))

        return self._image

    def get_frame(self, root, col: int, row: int) -> tk.PhotoImage:
        key = (col, row)
        if key in self._frames:
            return self._frames[key]

        if self._image is None:
            self.load(root)

        if HAS_PIL and self._pil_image is not None:
            frame = self._extract_pil_frame(col, row)
        else:
            frame = self._extract_tk_frame(col, row)

        self._frames[key] = frame
        return frame

    def _extract_pil_frame(self, col: int, row: int) -> tk.PhotoImage:
        x = col * self._frame_width
        y = row * self._frame_height
        box = (x, y, x + self._frame_width, y + self._frame_height)
        frame_pil = self._pil_image.crop(box)
        return ImageTk.PhotoImage(frame_pil)

    def _extract_tk_frame(self, col: int, row: int) -> tk.PhotoImage:
        x = col * self._frame_width
        y = row * self._frame_height
        # tkinter PhotoImage copy with region: copy region x1 y1 x2 y2
        frame = self._image.copy(
            f"{x} {y} {x + self._frame_width} {y + self._frame_height}"
        )
        return frame

    @property
    def frame_width(self) -> int:
        return self._frame_width

    @property
    def frame_height(self) -> int:
        return self._frame_height

    @property
    def cols(self) -> int:
        if self._image is None:
            return 0
        width = self._image.width() if hasattr(self._image, 'width') else 0
        return width // self._frame_width if self._frame_width > 0 else 0

    @property
    def rows(self) -> int:
        if self._image is None:
            return 0
        height = self._image.height() if hasattr(self._image, 'height') else 0
        return height // self._frame_height if self._frame_height > 0 else 0

    @property
    def total_frames(self) -> int:
        return self.cols * self.rows


def load_image(root, path: str | Path) -> tk.PhotoImage:
    if HAS_PIL:
        img = Image.open(path)
        return ImageTk.PhotoImage(img)
    return tk.PhotoImage(file=str(path))
