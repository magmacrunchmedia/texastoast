"""Shared fixtures.

Some of the engine is only meaningful against a real tkinter canvas. Those
tests are skipped rather than failed when no display is available, so the
suite still runs on a headless machine.

There are two distinct ways tkinter can be unusable, and only one of them used
to be handled. "Installed but no display" was; "not installed at all" was not,
because the import below sat at module scope — so on a Raspberry Pi OS Lite
image, where tkinter is a separate ``python3-tk`` package, the suite failed to
*collect* rather than skipping. Both now fold into ``TK_AVAILABLE``.

One Tk root is created for the whole session and never torn down early. Both
parts matter: creating a second root after destroying the first fails on some
Tcl builds ("couldn't read file init.tcl"), so the availability probe keeps
the root it made rather than discarding it.
"""
import os

import pytest

try:
    import tkinter as tk
except ImportError:  # tkinter not installed at all
    tk = None

if tk is None:
    _ROOT = None
else:
    try:
        _ROOT = tk.Tk()
        _ROOT.withdraw()
    except Exception:  # no display, or no usable Tcl
        _ROOT = None

TK_AVAILABLE = _ROOT is not None

_TK_SKIP_REASON = (
    "tkinter is not installed" if tk is None else "no display available for tkinter"
)

requires_tk = pytest.mark.skipif(not TK_AVAILABLE, reason=_TK_SKIP_REASON)

# Skipping is right on a developer's headless box, but in CI it would turn a
# broken display setup into a silent green run that tests none of the renderer,
# loop, Game lifecycle or editor. CI sets this to make that a hard failure.
REQUIRE_TK = os.environ.get("TEXASTOAST_REQUIRE_TK") == "1"


def pytest_configure(config):
    if REQUIRE_TK and not TK_AVAILABLE:
        raise pytest.UsageError(
            f"TEXASTOAST_REQUIRE_TK=1 but {_TK_SKIP_REASON}, so the UI tests "
            "would silently skip. Install tkinter (python3-tk on Debian) and a "
            "display (xvfb-run on Linux), or unset the variable."
        )


@pytest.fixture
def tk_root():
    """The shared Tk root, cleaned of per-test state afterwards."""
    if _ROOT is None:
        pytest.skip("no display available for tkinter")
    yield _ROOT
    for child in _ROOT.winfo_children():
        try:
            child.destroy()
        except tk.TclError:
            pass
    for sequence in _ROOT.bind():
        try:
            _ROOT.unbind(sequence)
        except tk.TclError:
            pass


def pytest_sessionfinish(session, exitstatus):
    if _ROOT is not None:
        try:
            _ROOT.destroy()
        except tk.TclError:
            pass
