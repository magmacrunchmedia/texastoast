"""Turns a missing optional backend into the command that installs it.

The engine declares zero required dependencies, so a backend import can fail on
a perfectly healthy install. ``ModuleNotFoundError: No module named 'tkinter'``
names the module but not the fix, and for tkinter the fix is not a pip install
at all: it ships with CPython on Windows and macOS, but Debian and Raspberry Pi
OS package it separately as ``python3-tk``. No amount of
``pip install texastoast`` repairs that, which is why the message has to name
the platform's own package manager.

This module must keep importing nothing beyond the standard library's cheapest
pieces — it is reached from the lazy hooks that exist to avoid imports.
"""

from __future__ import annotations

import sys

#: Reached when tkinter is absent. Keyed by ``sys.platform``; the Linux entry is
#: the one that matters in practice, since a Raspberry Pi OS Lite image has
#: neither tkinter nor a display.
_TK_FIXES = {
    "linux": "sudo apt install python3-tk    # Debian/Ubuntu/Raspberry Pi OS",
    "darwin": "brew install python-tk",
    "win32": "re-run the Python installer and enable 'tcl/tk and IDLE'",
}

#: Names that mean "Tk is missing" rather than "something inside the backend is
#: broken". ``_tkinter`` is the C extension: on some Linux builds the Python
#: half is present and only this is absent, which fails just as hard.
_TK_MODULES = frozenset({"tkinter", "_tkinter"})


def reraise_tk(name: str, exc: ImportError) -> None:
    """Re-raise *exc* with the fix in it, if tkinter is what went missing.

    Returns normally when the failure was anything else, so the caller's bare
    ``raise`` re-surfaces the original error. Without that check an unrelated
    broken import inside a backend module would be reported as a missing Tk,
    sending the reader off to install a package they already have.
    """
    if getattr(exc, "name", None) not in _TK_MODULES:
        return

    fix = _TK_FIXES.get(sys.platform, "install your platform's Tk package for Python")
    raise ImportError(
        f"{name} needs tkinter, which is not available. Install it with:\n"
        f"    {fix}\n"
        f"tkinter ships with Python but is not always installed alongside it, and "
        f"pip cannot supply it. To run without a display instead, use the "
        f'terminal backend: pip install "texastoast[tui]" and build a TuiGame.'
    ) from exc
