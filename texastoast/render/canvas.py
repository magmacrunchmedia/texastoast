from __future__ import annotations

import tkinter as tk
from collections.abc import Iterable

from texastoast.render.camera import Camera


class CanvasRenderer:
    """Renders tiles, sprites, and layers onto a tkinter Canvas.

    Satisfies both :class:`~texastoast.render.abstract.Renderer` (world-space
    drawing) and :class:`~texastoast.render.abstract.UISurface` (screen-space
    widget drawing) — structurally, no inheritance. UI widgets can therefore
    take the renderer directly instead of a bare canvas plus their own copy
    of the window size.
    """

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

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def clear(self):
        self._canvas.delete("all")

    def present(self):
        """No-op on tkinter — the Canvas is retained-mode.

        Call it at the end of your render function anyway: a buffered backend
        (SDL, framebuffer) flips its off-screen buffer here, and that habit
        cannot be retrofitted later without touching every game.
        """

    def draw_tilemap(self, tilemap, tile_colors: dict[int, str],
                     skip_tiles: Iterable[int] | None = None):
        """Draw the visible region of ``tilemap``.

        A tile is drawn when its id has an entry in ``tile_colors``; ids that
        are absent are left transparent, as are any listed in ``skip_tiles``.
        """
        cam = self._camera
        ts = tilemap.tile_size
        skip = set(skip_tiles) if skip_tiles is not None else None

        start_col = max(0, int(cam.x // ts))
        end_col = min(tilemap.cols, int((cam.x + self._width) // ts) + 2)
        start_row = max(0, int(cam.y // ts))
        end_row = min(tilemap.rows, int((cam.y + self._height) // ts) + 2)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_id = tilemap.get(col, row)
                if skip is not None and tile_id in skip:
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

    # ── UISurface ───────────────────────────────────────────────────
    # Screen-space widget drawing. A "group" maps onto a canvas tag here:
    # each widget owns one group and clears only that, so widgets compose
    # over a renderer that wipes the whole canvas each frame.

    def begin_group(self, group: str):
        self._canvas.delete(group)

    def clear_group(self, group: str):
        self._canvas.delete(group)

    def ui_rect(self, x: float, y: float, w: float, h: float, *,
                fill: str, outline: str = "", outline_width: int = 0,
                group: str = ""):
        self._canvas.create_rectangle(
            x, y, x + w, y + h,
            fill=fill, outline=outline, width=outline_width, tags=group,
        )

    def ui_text(self, x: float, y: float, text: str, *,
                fill: str, font=None, anchor: str = "nw",
                width: float | None = None, group: str = ""):
        kwargs = {"text": text, "fill": fill, "anchor": anchor, "tags": group}
        if font is not None:
            kwargs["font"] = font
        if width is not None:
            kwargs["width"] = width
        self._canvas.create_text(x, y, **kwargs)
