"""texastoast must keep working with none of its optional extras installed.

The engine declares zero required runtime dependencies, and the terminal
backend must not quietly change that. Textual is heavy — it pulls Rich,
markdown-it, linkify, and more — so importing it as a side effect of
``import texastoast`` would make every Pi install pay for a backend most games
do not use.

Each check runs in a subprocess: once the test session has imported Textual for
the backend tests, ``sys.modules`` in *this* process can no longer answer the
question.
"""

import subprocess
import sys
import textwrap

import pytest


def _probe(body: str) -> str:
    """Run ``body`` in a clean interpreter and return its stdout."""
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(body)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.fail(f"probe failed:\n{result.stdout}\n{result.stderr}")
    return result.stdout.strip()


def test_importing_the_package_pulls_no_optional_dependency():
    out = _probe("""
        import sys
        import texastoast
        loaded = [m for m in ("textual", "rich", "tkinter", "pygame", "PIL", "smbus2")
                  if m in sys.modules]
        print(",".join(loaded))
    """)
    assert out == "", f"import texastoast pulled in: {out}"


def test_importing_render_pulls_no_backend():
    out = _probe("""
        import sys
        import texastoast.render
        loaded = [m for m in ("textual", "rich", "tkinter", "PIL") if m in sys.modules]
        print(",".join(loaded))
    """)
    assert out == "", f"import texastoast.render pulled in: {out}"


def test_the_cell_buffer_is_reachable_with_nothing_installed():
    # The half of the terminal backend a future ANSI stack reuses. If this ever
    # needs Textual, the split has failed.
    out = _probe("""
        import sys
        from texastoast.render.cellbuffer import CellBuffer
        buf = CellBuffer(4, 1)
        buf.write(0, 0, "ok")
        print(buf.to_text(), "textual" in sys.modules, "tkinter" in sys.modules)
    """)
    assert out == "ok False False"


def test_the_tui_renderer_is_reachable_with_no_terminal_library():
    # TuiRenderer draws into a buffer and flushes to an injected surface, so it
    # is usable — and testable — without Textual present.
    out = _probe("""
        import sys
        from texastoast.render.tui import TuiRenderer
        r = TuiRenderer(6, 1)
        r.draw_hud_text(0, 0, "hi")
        r.present()
        print(r.to_text(), "textual" in sys.modules, "curses" in sys.modules)
    """)
    assert out == "hi False False"


def test_the_scheduler_protocol_needs_nothing():
    out = _probe("""
        import sys
        from texastoast.core.scheduler import ManualScheduler, Scheduler
        print(isinstance(ManualScheduler(), Scheduler), "tkinter" in sys.modules)
    """)
    assert out == "True False"


def test_the_game_loop_needs_no_tkinter():
    # The point of naming the Scheduler seam: the loop is no longer tied to tk.
    out = _probe("""
        import sys
        from texastoast.core.loop import GameLoop
        from texastoast.core.scheduler import ManualScheduler
        sched = ManualScheduler()
        ticks = []
        loop = GameLoop(sched, lambda dt: ticks.append(dt), lambda: None, fps=30)
        loop.start()
        sched.tick(3)
        loop.stop()
        print(len(ticks), "tkinter" in sys.modules)
    """)
    assert out == "4 False"


def test_asking_for_the_tui_host_without_the_extra_explains_itself():
    # Simulate the extra being absent by blocking the import, and check the
    # error names the fix rather than surfacing a bare ModuleNotFoundError.
    out = _probe("""
        import sys
        sys.modules["textual"] = None  # force ImportError on `import textual`
        import texastoast
        try:
            texastoast.TuiGame
        except ImportError as exc:
            print("guided" if "texastoast[tui]" in str(exc) else f"unhelpful: {exc}")
        else:
            print("no error raised")
    """)
    assert out == "guided"
