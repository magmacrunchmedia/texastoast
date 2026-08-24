from texastoast.input.abstract import InputState


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


def test_input_state_is_any_direction():
    s = InputState()
    assert s.is_any_direction() is False
    s = InputState(up=True)
    assert s.is_any_direction() is True
    s = InputState(a=True)
    assert s.is_any_direction() is False
