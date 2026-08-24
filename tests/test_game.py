"""Game lifecycle tests.

These build the Game against the shared session root. Creating a fresh Tk per
test is not an option: on some Tcl builds, creating a root after another has
been destroyed fails with `invalid command name "tcl_findLibrary"`.
"""
import pytest
from conftest import requires_tk

from texastoast.core.game import Game
from texastoast.input.keyboard import KeyboardInput

pytestmark = requires_tk


@pytest.fixture
def game(tk_root):
    g = Game(title="test", width=64, height=64, fps=30, root=tk_root)
    yield g
    g.quit()


def test_window_close_runs_quit(tk_root):
    # Regression: closing the window with the X button left the loop running
    # with a pending after() callback, because nothing handled the protocol.
    import tkinter as tk

    window = tk.Toplevel(tk_root)
    try:
        game = Game(width=64, height=64, root=window)
        fired = []
        game.on_close(lambda: fired.append(1))

        handler = window.protocol("WM_DELETE_WINDOW")
        assert handler, "WM_DELETE_WINDOW must be handled"

        # Invoke the Tcl command the window manager would invoke on close.
        window.tk.call(handler)
        assert fired == [1], "closing the window must run quit()"
    finally:
        if window.winfo_exists():
            window.destroy()


def test_embedded_frame_root_needs_no_close_protocol(tk_root):
    import tkinter as tk

    frame = tk.Frame(tk_root)
    game = Game(width=64, height=64, root=frame)  # must not raise
    assert game.root is frame
    game.quit()
    assert frame.winfo_exists()


def test_an_injected_root_is_not_destroyed_by_quit(tk_root):
    game = Game(width=64, height=64, root=tk_root)
    game.quit()
    # The caller's root is still usable.
    assert tk_root.winfo_exists()


def test_on_close_callbacks_run_on_quit(game):
    calls = []
    game.on_close(lambda: calls.append("first"))
    game.on_close(lambda: calls.append("second"))
    game.quit()
    assert calls == ["first", "second"]


def test_a_failing_teardown_callback_does_not_block_the_others(game):
    calls = []

    def boom():
        raise RuntimeError("nope")

    game.on_close(boom)
    game.on_close(lambda: calls.append("ran"))
    game.quit()
    assert calls == ["ran"]


def test_quit_is_idempotent(game):
    calls = []
    game.on_close(lambda: calls.append(1))
    game.quit()
    game.quit()  # must not raise, and must not re-run teardown
    assert calls == [1]


def test_keyboard_destroy_can_be_registered_as_teardown(game):
    keyboard = KeyboardInput(game.root)
    game.on_close(keyboard.destroy)
    assert keyboard._bindings
    game.quit()
    assert keyboard._bindings == []


def test_keyboard_destroy_unbinds_and_resets_state(tk_root):
    keyboard = KeyboardInput(tk_root)
    keyboard._set("up", True)
    assert keyboard.poll().up is True

    keyboard.destroy()
    assert keyboard._bindings == []
    assert keyboard.poll().up is False
    keyboard.destroy()  # idempotent
