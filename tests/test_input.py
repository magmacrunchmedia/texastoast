from conftest import requires_tk

from texastoast.input.abstract import InputState

# KeyboardInput is imported inside the two tests that use it, not here: it
# pulls tkinter, and the four InputState tests below are pure logic that must
# still run on a machine without it. @requires_tk covers those two.


def test_input_state_defaults():
    s = InputState()
    assert s.up is False
    assert s.down is False
    assert s.left is False
    assert s.right is False
    assert s.a is False
    assert s.b is False
    assert s.start is False
    assert s.select is False


def test_input_state_dx():
    s = InputState(left=True)
    assert s.dx == -1.0
    s = InputState(right=True)
    assert s.dx == 1.0
    s = InputState(left=True, right=True)
    assert s.dx == 0.0


def test_input_state_dy():
    s = InputState(up=True)
    assert s.dy == -1.0
    s = InputState(down=True)
    assert s.dy == 1.0
    s = InputState(up=True, down=True)
    assert s.dy == 0.0


def test_input_state_is_any_direction():
    s = InputState()
    assert s.is_any_direction() is False
    s = InputState(up=True)
    assert s.is_any_direction() is True
    s = InputState(a=True)
    assert s.is_any_direction() is False


@requires_tk
def test_keys_sharing_a_button_do_not_release_each_other(tk_root):
    """Up/w/W all map to `up`, Left/a/A all map to `left`.

    Releasing one alias used to clear the button outright, so holding Left and
    tapping `a` stopped the player mid-stride.
    """
    from texastoast.input.keyboard import KeyboardInput

    keyboard = KeyboardInput(tk_root)

    keyboard._press("Left", "left")
    keyboard._press("a", "left")
    assert keyboard.poll().left is True

    keyboard._release("a", "left")
    assert keyboard.poll().left is True   # the arrow is still down

    keyboard._release("Left", "left")
    assert keyboard.poll().left is False


@requires_tk
def test_poll_returns_a_snapshot_not_the_live_state(tk_root):
    """Edge detection needs the previous frame to stay put."""
    from texastoast.input.keyboard import KeyboardInput

    keyboard = KeyboardInput(tk_root)

    previous = keyboard.poll()
    keyboard._press("z", "a")
    current = keyboard.poll()

    assert previous is not current
    assert previous.a is False
    assert current.a is True
