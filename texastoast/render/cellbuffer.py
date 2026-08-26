"""A character-cell framebuffer — the shared substrate of every terminal backend.

This module is deliberately framework-free: no Textual, no Rich, no curses, no
tkinter. It is the half of a terminal backend that has nothing to do with *which*
terminal library is driving it, so it lives on its own rather than inside
:mod:`texastoast.render.tui`.

The split matters because a hand-written ANSI backend is a stated long-term goal.
When that arrives it consumes this buffer and adds only the parts that are
genuinely ANSI-specific — raw mode, an SGR-tracking diff emitter, escape-sequence
input decoding. Keeping the buffer out here means that backend is an addition
rather than a rewrite, and that both backends can be tested against the same
cell-level assertions with nothing installed.

One buffer cell is one character cell. Coordinates are integer cells, origin
top-left. Anything a game wants in pixels is scaled by the *game*, never here.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

#: Drawn for a cell nothing has written to this frame.
EMPTY_CHAR = " "


@dataclass(frozen=True, slots=True)
class Cell:
    """One character cell: a glyph plus its colors.

    Colors are hex strings (``"#e94560"``) or ``None`` for "inherit the
    terminal default". Hex is the vocabulary the render protocols already speak
    and the one Rich consumes natively, so no translation happens at this layer.
    A backend targeting a 16- or 256-color terminal quantizes on its way out.
    """

    char: str = EMPTY_CHAR
    fg: str | None = None
    bg: str | None = None

    @property
    def is_blank(self) -> bool:
        """True when this cell would render as untouched background."""
        return self.char == EMPTY_CHAR and self.fg is None and self.bg is None


EMPTY_CELL = Cell()


@dataclass
class CellBuffer:
    """A resizable grid of :class:`Cell`, with group-scoped erasure.

    Writes clip silently at the edges. Out-of-bounds is the normal case for a
    game — an entity walks off-screen, a HUD string is longer than the terminal
    is wide — so it is not worth an exception on every frame.
    """

    width: int
    height: int
    _cells: list[list[Cell]] = field(init=False, repr=False)
    #: group name -> the (x, y) cells that group has written this frame.
    _groups: dict[str, set[tuple[int, int]]] = field(
        init=False, repr=False, default_factory=dict
    )
    #: The group currently being written to, set by :meth:`begin_group`.
    _active_group: str = field(init=False, repr=False, default="")

    def __post_init__(self) -> None:
        self.width = max(0, int(self.width))
        self.height = max(0, int(self.height))
        self._cells = self._blank_grid(self.width, self.height)

    @staticmethod
    def _blank_grid(width: int, height: int) -> list[list[Cell]]:
        return [[EMPTY_CELL] * width for _ in range(height)]

    # ── Frame lifecycle ─────────────────────────────────────────────

    def clear(self) -> None:
        """Blank every cell and forget all group bookkeeping.

        Called once per frame by the renderer. Group membership is per-frame:
        a widget that stops drawing simply stops claiming cells.
        """
        self._cells = self._blank_grid(self.width, self.height)
        self._groups.clear()
        self._active_group = ""

    def resize(self, width: int, height: int) -> None:
        """Resize the grid, discarding contents.

        Contents are dropped rather than reflowed because the next frame
        repaints everything anyway, and guessing how a game's layout should
        reflow is the game's business. A no-op when the size is unchanged, so
        this is safe to call from a resize event that fires spuriously.
        """
        width = max(0, int(width))
        height = max(0, int(height))
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self.clear()

    # ── Groups ──────────────────────────────────────────────────────
    #
    # ``UISurface`` organizes widget drawing into named groups. On a retained
    # canvas a group is a tag and erasing it is a delete. Here the frame is
    # already blank at the top of each render, so ``begin_group`` only needs to
    # take ownership of subsequent writes; ``clear_group`` is the one that has
    # to do real work, because a widget may be dismissed mid-frame.

    @property
    def active_group(self) -> str:
        """The group subsequent writes are attributed to; ``""`` for none.

        Settable, because a widget that draws several times in one frame needs
        to keep accumulating into its group without ``begin_group`` wiping what
        it drew a call ago.
        """
        return self._active_group

    @active_group.setter
    def active_group(self, group: str) -> None:
        self._active_group = group or ""

    def begin_group(self, group: str) -> None:
        """Make ``group`` the owner of subsequent writes, discarding its old cells."""
        self.clear_group(group)
        self._active_group = group

    def end_group(self) -> None:
        """Stop attributing writes to the active group."""
        self._active_group = ""

    def clear_group(self, group: str) -> None:
        """Blank exactly the cells ``group`` wrote, leaving every other group intact."""
        owned = self._groups.pop(group, None)
        if not owned:
            return
        for x, y in owned:
            if 0 <= y < self.height and 0 <= x < self.width:
                self._cells[y][x] = EMPTY_CELL
        if self._active_group == group:
            self._active_group = ""

    def _claim(self, x: int, y: int) -> None:
        if self._active_group:
            self._groups.setdefault(self._active_group, set()).add((x, y))

    # ── Drawing ─────────────────────────────────────────────────────

    def set_cell(self, x: int, y: int, char: str, fg: str | None = None,
                 bg: str | None = None) -> None:
        """Write a single cell. Silently ignored when out of bounds."""
        x = int(x)
        y = int(y)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self._cells[y][x] = Cell(char, fg, bg)
        self._claim(x, y)

    def get(self, x: int, y: int) -> Cell:
        """Read a cell. Out-of-bounds reads give a blank cell rather than raising."""
        x = int(x)
        y = int(y)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return EMPTY_CELL
        return self._cells[y][x]

    def write(self, x: int, y: int, text: str, fg: str | None = None,
              bg: str | None = None) -> None:
        """Write ``text`` rightwards from ``(x, y)``, clipping at the edges.

        Newlines start a fresh line back at the original ``x``, so a multi-line
        string keeps its left margin. Rows past the bottom are dropped.
        """
        if not text:
            return
        row = int(y)
        for line in text.split("\n"):
            if row >= self.height:
                return
            if row >= 0:
                col = int(x)
                for ch in line:
                    if col >= self.width:
                        break
                    if col >= 0:
                        self._cells[row][col] = Cell(ch, fg, bg)
                        self._claim(col, row)
                    col += 1
            row += 1

    def fill(self, x: int, y: int, w: int, h: int, bg: str | None = None,
             char: str = EMPTY_CHAR, fg: str | None = None) -> None:
        """Fill a rectangle, clipped to the buffer.

        Defaults to painting background only — a filled ``draw_rect`` in a
        terminal is a block of spaces with a background color.
        """
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.width, int(x) + int(w))
        y1 = min(self.height, int(y) + int(h))
        if x1 <= x0 or y1 <= y0:
            return
        cell = Cell(char, fg, bg)
        for row in range(y0, y1):
            line = self._cells[row]
            for col in range(x0, x1):
                line[col] = cell
                self._claim(col, row)

    def outline(self, x: int, y: int, w: int, h: int, color: str | None = None,
                char: str = "", *, fg: str | None = None) -> None:
        """Stroke the border of a rectangle one cell thick.

        With ``char`` empty the border is drawn as background color (the
        terminal equivalent of a hairline outline); pass a glyph such as ``"#"``
        to stroke with a character instead.
        """
        if int(w) <= 0 or int(h) <= 0:
            return
        stroke_bg = None if char else color
        stroke_fg = fg if fg is not None else (color if char else None)
        glyph = char or EMPTY_CHAR
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + int(w) - 1, y0 + int(h) - 1
        for col in range(x0, x1 + 1):
            self.set_cell(col, y0, glyph, stroke_fg, stroke_bg)
            self.set_cell(col, y1, glyph, stroke_fg, stroke_bg)
        for row in range(y0, y1 + 1):
            self.set_cell(x0, row, glyph, stroke_fg, stroke_bg)
            self.set_cell(x1, row, glyph, stroke_fg, stroke_bg)

    # ── Readback ────────────────────────────────────────────────────

    def row(self, y: int) -> list[Cell]:
        """A copy of one row, for a backend to convert into its own line type."""
        if not (0 <= int(y) < self.height):
            return []
        return list(self._cells[int(y)])

    def rows(self):
        """Iterate rows top to bottom."""
        for y in range(self.height):
            yield list(self._cells[y])

    def to_text(self) -> str:
        """The buffer as plain text, colors discarded.

        For tests and snapshots — asserting on a string is far easier to read
        than asserting on a grid of cells.
        """
        return "\n".join(
            "".join(cell.char for cell in row).rstrip() for row in self._cells
        )

    def replace_cell(self, x: int, y: int, **changes) -> None:
        """Modify parts of an existing cell, keeping the rest.

        Useful for painting a background under text that is already there,
        without having to know what glyph is sitting in the cell.
        """
        x = int(x)
        y = int(y)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self._cells[y][x] = replace(self._cells[y][x], **changes)
        self._claim(x, y)
