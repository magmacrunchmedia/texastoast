"""Block lettering — a title in a terminal, when a bigger font is not an option.

A terminal program does not choose its font. Whatever the person running it
has their emulator set to is what every string renders in, and there is no
equivalent of ``font-family`` to reach for. A game that wants its title to look
like a title therefore has to *draw* the letters, out of characters that are
geometry rather than type: block elements look the same in every monospace
font, because they fill their cell.

That is what this is. It is not a text renderer and not a widget - it turns a
string into lines, and the caller draws them however it draws anything else::

    from texastoast.ui import bigtext

    for i, line in enumerate(bigtext.lines("LAVA DOME")):
        renderer.ui_text(x, y + i, line, fill=theme.TITLE)

**The face is fixed-width**, four columns of ink and a fifth of gutter, three
rows tall. Fixed rather than fitted because that is what the arcade lettering
it is imitating does, and because a caller laying a title out can then work
out where it lands with :func:`width` instead of rendering it to find out.

Three rows rather than two: a two-row block face cannot tell ``B`` from ``D``
or ``O`` from ``Q`` without reaching for quadrant glyphs, and a title screen
that renders BOOLE as DOOLE is worse than one in plain capitals.

Unsupported characters render as a blank cell rather than raising. A title is
decoration, and decoration should not be able to take a game down.
"""

from __future__ import annotations

#: Columns of ink per glyph, before the gutter.
GLYPH_W = 4
#: Columns each glyph occupies including its gutter.
ADVANCE = 5
#: Rows every glyph is tall.
GLYPH_H = 3

# Authored as three strings per glyph, each exactly GLYPH_W wide. Written out
# rather than generated because a letterform is a drawing, and the only way to
# know an S reads as an S is to look at it - tests/test_bigtext.py renders the
# whole alphabet for exactly that reason.
_FONT: dict[str, tuple[str, str, str]] = {
    "A": ("▄██▄", "█▀▀█", "█  █"),
    "B": ("███▄", "█▀▀▄", "███▀"),
    "C": ("▄███", "█   ", "▀███"),
    "D": ("███▄", "█  █", "███▀"),
    "E": ("████", "██▀ ", "████"),
    "F": ("████", "██▀ ", "█   "),
    "G": ("▄███", "█ ▀█", "▀███"),
    "H": ("█  █", "████", "█  █"),
    "I": ("▀██▀", " ██ ", "▄██▄"),
    "J": ("▀███", "  █ ", "▀██▀"),
    # The arm has to actually leave the stem, or K is an H with a chipped bar.
    "K": ("█ ▄█", "██▀ ", "█ ▀█"),
    "L": ("█   ", "█   ", "████"),
    "M": ("█▄▄█", "█▀▀█", "█  █"),
    "N": ("██ █", "█▀██", "█  █"),
    "O": ("▄██▄", "█  █", "▀██▀"),
    "P": ("███▄", "███▀", "█   "),
    "Q": ("▄██▄", "█  █", "▀███"),
    "R": ("███▄", "███▀", "█  █"),
    "S": ("▄███", "▀██▄", "███▀"),
    "T": ("████", " ██ ", " ██ "),
    "U": ("█  █", "█  █", "▀██▀"),
    "V": ("█  █", "█  █", "▀▄▄▀"),
    "W": ("█  █", "█▄▄█", "▀██▀"),
    # Pinched at the waist rather than barred, so it does not collide with Y.
    "X": ("█  █", " ██ ", "█  █"),
    "Y": ("█  █", "▀██▀", " ██ "),
    "Z": ("████", " ▄█▀", "████"),
    "0": ("▄██▄", "█ ▄█", "▀██▀"),
    "1": (" ▄█ ", "  █ ", " ▄█▄"),
    "2": ("▄██▄", " ▄█▀", "████"),
    "3": ("███▄", " ██▄", "███▀"),
    "4": ("█  █", "████", "   █"),
    "5": ("████", "███▄", "███▀"),
    "6": ("▄███", "███▄", "▀██▀"),
    "7": ("████", "  █▀", " █  "),
    "8": ("▄██▄", "▄██▄", "▀██▀"),
    "9": ("▄██▄", "▀███", "███▀"),
    "'": (" █  ", "    ", "    "),
    ".": ("    ", "    ", " ▄  "),
    "!": (" ██ ", " ██ ", " ▄  "),
    "?": ("███▄", " ▄█▀", " ▄  "),
    "-": ("    ", "████", "    "),
    ":": (" ▄  ", "    ", " ▄  "),
    " ": ("    ", "    ", "    "),
}

#: What an unsupported character renders as. Blank rather than a tofu box, so
#: a stray character leaves a gap instead of a smear.
_MISSING = ("    ", "    ", "    ")


def supports(char: str) -> bool:
    """Whether ``char`` has a glyph. Case-insensitive; the face is capitals."""
    return char.upper() in _FONT


def _row_width(text: str) -> int:
    if not text:
        return 0
    return len(text) * ADVANCE - (ADVANCE - GLYPH_W)


def width(text: str) -> int:
    """Columns :func:`lines` will produce for ``text``, gutter excluded.

    For multi-line text this is the widest row, since the block comes back
    padded to a rectangle.
    """
    return max((_row_width(row) for row in text.split("\n")), default=0)


def height(text: str) -> int:
    """Rows :func:`lines` will produce for ``text``."""
    return len(text.split("\n")) * GLYPH_H


def lines(text: str) -> list[str]:
    """``text`` as block lettering, :data:`GLYPH_H` rows per line of input.

    A newline breaks the title, the way ``<br>`` does in a card title on the
    web — the long names in this family are written that way there
    (``TEXAS HOLD'EM<br>LAVA DOME``), and a name that only fits by being cut
    short is not the name.

    Every line comes back the same length and each row of input is centred
    within that, so the whole thing can be centred as one block. Centring the
    lines individually would ragged it apart: the top row of a word beginning
    in ``L`` is mostly empty.
    """
    if not text:
        return [""] * GLYPH_H

    total = width(text)
    out: list[str] = []
    for row_text in text.split("\n"):
        glyphs = [_FONT.get(char.upper(), _MISSING) for char in row_text]
        pad = (total - _row_width(row_text)) // 2
        for row in range(GLYPH_H):
            drawn = " ".join(glyph[row] for glyph in glyphs)
            out.append((" " * pad + drawn).ljust(total))
    return out


def block(text: str) -> str:
    """:func:`lines`, joined. The form :mod:`banner`-style ladders want."""
    return "\n".join(lines(text))


def fits(text: str, cols: int, rows: int = GLYPH_H) -> bool:
    """Whether ``text`` renders inside ``cols`` x ``rows``.

    A caller with several candidate titles - the name broken over two lines,
    the name on one, plain capitals - can walk them and take the first that
    fits, which is what a resizable window needs.
    """
    return width(text) <= cols and height(text) <= rows


__all__ = ["ADVANCE", "GLYPH_H", "GLYPH_W", "block", "fits", "height", "lines",
           "supports", "width"]
