"""The block face.

A letterform is a drawing, and the only way to know an S reads as an S is to
look at one - so the useful half of this file is
:func:`test_render_the_whole_face`, which prints it. Run with ``-s`` to see it.

The rest guards the properties a caller depends on: every glyph the same size,
no two glyphs identical, and the width a caller is told to expect being the
width it gets.
"""

import pytest

from texastoast.ui import bigtext

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIGITS = "0123456789"


def test_every_glyph_is_the_same_size():
    """Fixed-width is the whole reason `width` can be computed rather than
    measured, and the reason a caller can lay a title out before rendering it."""
    for char, glyph in bigtext._FONT.items():
        assert len(glyph) == bigtext.GLYPH_H, char
        for row in glyph:
            assert len(row) == bigtext.GLYPH_W, f"{char}: {row!r}"


def test_no_two_letters_share_a_glyph():
    """A face that renders BOOLE as DOOLE is worse than plain capitals. This
    is what three rows buy over two."""
    seen: dict[tuple, str] = {}
    for char, glyph in bigtext._FONT.items():
        if char == " ":
            continue
        assert glyph not in seen, f"{char} and {seen[glyph]} draw identically"
        seen[glyph] = char


def test_the_alphabet_and_digits_are_all_covered():
    for char in ALPHABET + DIGITS:
        assert bigtext.supports(char), char


def test_lowercase_renders_as_capitals():
    assert bigtext.lines("boole") == bigtext.lines("BOOLE")


def test_width_is_what_lines_actually_produces():
    for text in ("A", "AB", "GEORGE BOOLE", "LAVA DOME", "MAGMACRUNCH", ""):
        produced = {len(line) for line in bigtext.lines(text)}
        assert produced == {bigtext.width(text)}, text


def test_every_line_is_the_same_length_so_the_block_can_be_centred():
    """Centring the lines individually raggeds the block apart - the top row
    of a word beginning in L is mostly empty."""
    assert len({len(line) for line in bigtext.lines("LAVA DOME")}) == 1


def test_an_unsupported_character_is_a_gap_not_a_crash():
    """A title is decoration, and decoration must not be able to take a game
    down."""
    assert bigtext.lines("AéB") == bigtext.lines("A B")


def test_empty_text_still_gives_three_empty_rows():
    assert bigtext.lines("") == ["", "", ""]
    assert bigtext.width("") == 0


def test_fits_answers_before_anything_is_drawn():
    assert bigtext.fits("LAVA DOME", 44)
    assert not bigtext.fits("LAVA DOME", 43)
    assert not bigtext.fits("LAVA DOME", 80, rows=2)


def test_block_is_lines_joined():
    assert bigtext.block("HI").split("\n") == bigtext.lines("HI")


def test_a_space_draws_nothing():
    assert bigtext.lines(" ") == ["    "] * bigtext.GLYPH_H


@pytest.mark.parametrize("text", ["GEORGE BOOLE", "LAVA DOME", "MAGMACRUNCH"])
def test_the_titles_this_exists_for_fit_a_terminal(text):
    """The three wordmarks in the family. If the face ever grows wide enough
    that these stop fitting an 80-column window, it has stopped being useful."""
    assert bigtext.width(text) <= 78, f"{text} is {bigtext.width(text)} columns"


def _console_takes_block_glyphs() -> bool:
    """Whether stdout can encode the face at all.

    A Windows console on a legacy codepage cannot, and printing to it raises.
    The test below is a viewing aid rather than an assertion, so it stands
    aside rather than failing the suite over where it happens to be run.
    """
    import sys

    # ``sys.__stdout__``, not ``sys.stdout``: under pytest the latter is the
    # capture stream, which is UTF-8 whatever the console is - and it is the
    # console the print actually reaches, because capsys.disabled() hands it
    # back.
    stream = sys.__stdout__ or sys.stdout
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        "█▀▄".encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


@pytest.mark.skipif(not _console_takes_block_glyphs(),
                    reason="this console cannot encode block glyphs")
def test_render_the_whole_face(capsys):
    """Not an assertion - a way to look at it. ``pytest -s -k whole_face``."""
    with capsys.disabled():
        print()
        for chunk in (ALPHABET[:9], ALPHABET[9:18], ALPHABET[18:], DIGITS):
            for line in bigtext.lines(chunk):
                print(line)
            print()
