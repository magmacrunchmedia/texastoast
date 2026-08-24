from __future__ import annotations

import tkinter as tk

from texastoast.render.camera import Camera


class CanvasRenderer:
    """Renders tiles, sprites, and layers onto a tkinter Canvas."""

    def __init__(self, canvas: tk.Canvas, width: int, height: int):
        self._canvas = canvas
        self._width = width
        self._height = height
        self._camera = Camera(width, height)

    @property
    def canvas(self) -> tk.Canvas:
        return self._canvas

    @property
    def camera(self) -> Camera:
        return self._camera

    def clear(self):
        self._canvas.delete("all")

    def draw_tilemap(self, tilemap, tile_colors: dict[int, str],
                     skip_tiles: set[int] | None = None):
        """Draw the visible region of ``tilemap``.

        A tile is drawn when its id has an entry in ``tile_colors``; ids that
        are absent are left transparent, as are any listed in ``skip_tiles``.
        """
        cam = self._camera
        ts = tilemap.tile_size

        start_col = max(0, int(cam.x // ts))
        end_col = min(tilemap.cols, int((cam.x + self._width) // ts) + 2)
        start_row = max(0, int(cam.y // ts))
        end_row = min(tilemap.rows, int((cam.y + self._height) // ts) + 2)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_id = tilemap.get(col, row)
                if skip_tiles is not None and tile_id in skip_tiles:
                    continue
                color = tile_colors.get(tile_id)
                if color is None:
                    continue
                x1 = col * ts - cam.x
                y1 = row * ts - cam.y
                x2 = x1 + ts
                y2 = y1 + ts
                self._canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def draw_rect(self, x: float, y: float, w: float, h: float, color: str, tag: str = ""):
        cam = self._camera
        sx = x - cam.x
        sy = y - cam.y
        self._canvas.create_rectangle(sx, sy, sx + w, sy + h, fill=color, outline="", tags=tag)

    def draw_image(self, x: float, y: float, image: tk.PhotoImage, anchor: str = "nw", tag: str = ""):
        cam = self._camera
        sx = x - cam.x
        sy = y - cam.y
        self._canvas.create_image(sx, sy, image=image, anchor=anchor, tags=tag)

    def draw_text(self, x: float, y: float, text: str, **kwargs):
        cam = self._camera
        sx = x - cam.x
        sy = y - cam.y
        defaults = {"fill": "#ffffff", "anchor": "nw", "font": ("Courier", 10)}
        defaults.update(kwargs)
        self._canvas.create_text(sx, sy, text=text, **defaults)

    def draw_hud_text(self, x: float, y: float, text: str, **kwargs):
        """Draw text at screen-space coordinates (ignores camera)."""
        defaults = {"fill": "#ffffff", "anchor": "nw", "font": ("Courier", 10)}
        defaults.update(kwargs)
        self._canvas.create_text(x, y, text=text, **defaults)
