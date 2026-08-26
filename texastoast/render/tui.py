"""Terminal render backend — satisfies ``Renderer`` and ``UISurface`` over a cell grid.

This module imports no terminal library. It draws into a
:class:`~texastoast.render.cellbuffer.CellBuffer` and calls ``flush()`` on an
injected *surface* when the frame is done. Textual supplies that surface today
(:mod:`texastoast.core.tui_game`); a hand-written ANSI backend would supply a
different one and nothing here would change.

**One coordinate unit is one character cell, not a pixel.** A terminal cell is
roughly twice as tall as it is wide, and there is no sane universal pixel-to-cell
ratio, so this backend refuses to guess: ``width`` and ``height`` report cells,
and a game ported from a pixel canvas does its own scaling. Putting that scale
factor here would bake one game's aspect assumption into every other game.

What a terminal cannot honestly do is drawn as follows:

* ``draw_image`` is a no-op. Sprite sheets are the shared contract across
  adenosine/magnolia/texastoast, and a character grid has no way to honor them.
  Games wanting terminal art draw glyphs.
* Outlines one cell thick are the closest thing to a hairline stroke, so
  ``outline_width`` selects only *whether* a border is drawn, not how thick.
* Anti-aliasing, sub-cell positioning and proportional fonts do not exist;
  coordinates are truncated to whole cells.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from texastoast.render.camera import Camera
from texastoast.render.cellbuffer import EMPTY_CHAR, KEEP_BG, CellBuffer

logger = logging.getLogger(__name__)

#: Solid block, the default glyph for a filled tile.
FULL_BLOCK = "█"

#: Default foreground when a caller gives no color, matching CanvasRenderer.
DEFAULT_FG = "#ffffff"


class _NullSurface:
    """Stand-in surface for headless use — tests, and ``present()`` before attach."""

    def flush(self, buffer: CellBuffer) -> None:  # noqa: ARG002
        pass


class TuiRenderer:
    """Draws into a character-cell buffer.

    Satisfies both :class:`~texastoast.render.abstract.Renderer` and
    :class:`~texastoast.render.abstract.UISurface` structurally, exactly as
    :class:`~texastoast.render.canvas.CanvasRenderer` does, so UI widgets and
    game render functions work over either without knowing which they have.

    ``surface`` is anything with ``flush(buffer)``; it defaults to a no-op so a
    renderer can be built and asserted against with no terminal at all.
    """

    def __init__(self, width: int, height: int, surface: Any | None = None,
                 buffer: CellBuffer | None = None):
        self._buffer = buffer if buffer is not None else CellBuffer(width, height)
        self._surface = surface if surface is not None else _NullSurface()
        self._camera = Camera(width, height)
        #: Per-tile glyphs for ``draw_tilemap``. Not part of the Renderer
        #: protocol — a terminal needs a character where a canvas needs only a
        #: color, and adding it to the protocol would burden every backend with
        #: a concept only this one has. Ids absent here use ``default_tile_glyph``.
        self.tile_glyphs: dict[int, str] = {}
        self.default_tile_glyph: str = FULL_BLOCK
        self._warned_about_images = False

    # ── Wiring ──────────────────────────────────────────────────────

    @property
    def buffer(self) -> CellBuffer:
        return self._buffer

    @property
    def surface(self) -> Any:
        return self._surface

    def attach(self, surface: Any) -> None:
        """Point the renderer at a live surface (a Textual widget, say)."""
        self._surface = surface

    def resize(self, width: int, height: int) -> None:
        """Follow a terminal resize. The camera viewport tracks the new size."""
        self._buffer.resize(width, height)
        self._camera.width = self._buffer.width
        self._camera.height = self._buffer.height

    # ── Renderer ────────────────────────────────────────────────────

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def width(self) -> int:
        return self._buffer.width

    @property
    def height(self) -> int:
        return self._buffer.height

    def clear(self) -> None:
        self._buffer.clear()

    def present(self) -> None:
        """Push the finished frame to the surface.

        Unlike the tkinter backend this is *not* a no-op — the buffer is
        off-screen and nothing appears until it is flushed. This is the case
        ``present()`` was put in the protocol for.
        """
        self._surface.flush(self._buffer)

    def draw_tilemap(self, tilemap: Any, tile_colors: dict[int, str],
                     skip_tiles: Iterable[int] | None = None) -> None:
        """Draw the visible region of ``tilemap``, one cell per tile.

        Tiles are one cell here regardless of ``tilemap.tile_size`` — a 16-pixel
        tile has no meaning in a grid of characters, and scaling world
        coordinates by the tile size would put a 40x30 map far off-screen. The
        camera is therefore also interpreted in tiles for this call.
        """
        cam = self._camera
        skip = set(skip_tiles) if skip_tiles is not None else None

        start_col = max(0, int(cam.x))
        end_col = min(tilemap.cols, start_col + self.width + 1)
        start_row = max(0, int(cam.y))
        end_row = min(tilemap.rows, start_row + self.height + 1)

        for row in range(start_row, end_row):
            for col in range(start_col, end_col):
                tile_id = tilemap.get(col, row)
                if skip is not None and tile_id in skip:
                    continue
                color = tile_colors.get(tile_id)
                if color is None:
                    continue
                glyph = self.tile_glyphs.get(tile_id, self.default_tile_glyph)
                # A block glyph reads as a solid tile whether the terminal
                # honors foreground or background, so paint both.
                self._buffer.set_cell(col - start_col, row - start_row,
                                      glyph, fg=color, bg=color)

    def draw_rect(self, x: float, y: float, w: float, h: float,
                  color: str, tag: str = "") -> None:  # noqa: ARG002
        cam = self._camera
        self._buffer.fill(int(x - cam.x), int(y - cam.y), int(w), int(h), bg=color)

    def draw_image(self, x: float, y: float, image: Any,
                   anchor: str = "nw", tag: str = "") -> None:  # noqa: ARG002
        """No-op: a character grid cannot render a sprite sheet.

        Logged once at debug level rather than per frame — a game drawing
        sprites would otherwise emit thousands of identical lines a second.
        """
        if not self._warned_about_images:
            self._warned_about_images = True
            logger.debug(
                "TuiRenderer.draw_image is a no-op; a terminal has no pixels. "
                "Draw glyphs with draw_text, or set tile_glyphs for tilemaps."
            )

    def draw_text(self, x: float, y: float, text: str, **kwargs: Any) -> None:
        cam = self._camera
        self._write_text(x - cam.x, y - cam.y, text, kwargs)

    def draw_hud_text(self, x: float, y: float, text: str, **kwargs: Any) -> None:
        """Draw text in screen space, ignoring the camera."""
        self._write_text(x, y, text, kwargs)

    def _write_text(self, x: float, y: float, text: str, kwargs: dict[str, Any]) -> None:
        """Shared text path. Tk-only keyword arguments are accepted and ignored.

        Callers written for the canvas backend pass ``font=("Courier", 10)`` and
        similar. Rejecting those would mean every game needing a backend check
        at each call site, so they are dropped instead.
        """
        fill = kwargs.get("fill") or DEFAULT_FG
        # Absent means "composite over whatever is underneath", which is what a
        # canvas create_text does. Passing None here instead would clear the
        # background and cut a hole through the tile the text sits on.
        bg = kwargs["bg"] if "bg" in kwargs else KEEP_BG
        anchor = kwargs.get("anchor", "nw")
        text = str(text)
        ax, ay = self._anchor_offset(anchor, text)
        self._buffer.write(int(x) + ax, int(y) + ay, text, fg=fill, bg=bg)

    @staticmethod
    def _anchor_offset(anchor: str, text: str) -> tuple[int, int]:
        """Convert a tkinter anchor into a cell offset for ``text``.

        Only the compass anchors are meaningful on a grid. Vertical centring of
        a multi-line string uses its line count; horizontal uses the longest
        line, which is what a monospaced grid makes true.
        """
        lines = text.split("\n")
        w = max((len(line) for line in lines), default=0)
        h = len(lines)
        anchor = (anchor or "nw").lower()

        if anchor in ("nw", "w", "sw"):
            dx = 0
        elif anchor in ("ne", "e", "se"):
            dx = -w
        else:  # n, s, center/centre
            dx = -(w // 2)

        if anchor in ("nw", "n", "ne"):
            dy = 0
        elif anchor in ("sw", "s", "se"):
            dy = -h
        else:  # w, e, center/centre
            dy = -(h // 2)

        return dx, dy

    # ── UISurface ───────────────────────────────────────────────────
    #
    # Screen-space widget drawing. ``abstract.py`` allows an immediate-mode
    # backend to make begin_group a no-op because clear() already wiped the
    # frame — but clear_group must still work for a widget dismissed mid-frame,
    # so the buffer tracks which cells each group owns.

    def begin_group(self, group: str) -> None:
        self._buffer.begin_group(group)

    def clear_group(self, group: str) -> None:
        self._buffer.clear_group(group)

    def ui_rect(self, x: float, y: float, w: float, h: float, *,
                fill: str, outline: str = "", outline_width: int = 0,
                group: str = "") -> None:
        previous = self._enter_group(group)
        if fill:
            self._buffer.fill(int(x), int(y), int(w), int(h), bg=fill)
        # A border is either there or not; a terminal has no fractional cells,
        # so any positive width draws the same single-cell stroke.
        if outline and (outline_width > 0 or not fill):
            self._buffer.outline(int(x), int(y), int(w), int(h), color=outline)
        self._exit_group(previous)

    def ui_text(self, x: float, y: float, text: str, *,
                fill: str, font: Any = None, anchor: str = "nw",
                width: float | None = None, group: str = "") -> None:  # noqa: ARG002
        """Draw widget text. ``font`` is ignored — one cell, one glyph, no metrics.

        ``width`` wraps the text, matching the canvas backend's behaviour, but
        in cells rather than pixels.
        """
        previous = self._enter_group(group)
        rendered = self._wrap(str(text), width)
        ax, ay = self._anchor_offset(anchor, rendered)
        self._buffer.write(int(x) + ax, int(y) + ay, rendered, fg=fill or DEFAULT_FG)
        self._exit_group(previous)

    @staticmethod
    def _wrap(text: str, width: float | None) -> str:
        """Word-wrap to ``width`` cells, preserving explicit newlines."""
        if width is None or width <= 0:
            return text
        limit = int(width)
        out: list[str] = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split(" "):
                if not line:
                    line = word
                elif len(line) + 1 + len(word) <= limit:
                    line = f"{line} {word}"
                else:
                    out.append(line)
                    line = word
            out.append(line)
        return "\n".join(out)

    def _enter_group(self, group: str) -> str:
        """Attribute the next writes to ``group`` without discarding its cells.

        Distinct from ``begin_group``: a widget calls that once per frame to
        start fresh, then makes several draw calls that must all accumulate
        into the same group.
        """
        previous = self._buffer.active_group
        if group:
            self._buffer.active_group = group
        return previous

    def _exit_group(self, previous: str) -> None:
        self._buffer.active_group = previous

    # ── Readback ────────────────────────────────────────────────────

    def to_text(self) -> str:
        """The current frame as plain text — for tests and snapshots."""
        return self._buffer.to_text()


__all__ = ["TuiRenderer", "CellBuffer", "FULL_BLOCK", "EMPTY_CHAR"]
