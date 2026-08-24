"""Shared fixtures.

Some of the engine is only meaningful against a real tkinter canvas. Those
tests are skipped rather than failed when no display is available, so the
suite still runs on a headless machine.

One Tk root is created for the whole session and never torn down early. Both
parts matter: creating a second root after destroying the first fails on some
Tcl builds ("couldn't read file init.tcl"), so the availability probe keeps
the root it made rather than discarding it.
"""
import os
import tkinter as tk

import pytest

try:
    _ROOT = tk.Tk()
    _ROOT.withdraw()
except Exception:  # no display, or no usable Tcl
    _ROOT = None

TK_AVAILABLE = _ROOT is not None

requires_tk = pytest.mark.skipif(
    not TK_AVAILABLE, reason="no display available for tkinter"
)

# Skipping is right on a developer's headless box, but in CI it would turn a
# broken display setup into a silent green run that tests none of the renderer,
# loop, Game lifecycle or editor. CI sets this to make that a hard failure.
REQUIRE_TK = os.environ.get("TEXASTOAST_REQUIRE_TK") == "1"


def pytest_configure(config):
    if REQUIRE_TK and not TK_AVAILABLE:
        raise pytest.UsageError(
            "TEXASTOAST_REQUIRE_TK=1 but tkinter has no usable display, so the "
            "UI tests would silently skip. Install a display (xvfb-run on "
            "Linux) or unset the variable."
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
