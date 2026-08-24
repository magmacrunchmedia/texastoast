from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.protocol import (
    BTN_A,
    BTN_DOWN,
    BTN_LEFT,
    BTN_UP,
    ControllerState,
)
from texastoast.input.abstract import InputState
from texastoast.input.magma_hub import CompositeInput, MagmaHubInput


def test_i2cbus_mock_reads_report_failure():
    # A mock bus must not fabricate 0x00 data: callers have to be able to tell
    # "no hardware" apart from "a device that reported zero".
    bus = I2CBus(99)
    assert bus.is_mock is True
    assert bus.read_byte_data(0x08, 0) is None
    assert bus.read_i2c_block_data(0x08, 0, 2) is None
    bus.close()


def test_controller_state_buttons():
    cs = ControllerState(buttons=BTN_UP | BTN_A)
    assert cs.up is True
    assert cs.down is False
    assert cs.a is True
    assert cs.b is False


def test_controller_state_direction():
    cs = ControllerState(buttons=BTN_LEFT | BTN_DOWN)
    dx, dy = cs.direction()
    assert dx == -1.0
    assert dy == 1.0


def test_controller_state_all_buttons():
    cs = ControllerState(buttons=0xFF)
    assert cs.up is True
    assert cs.down is True
    assert cs.left is True
    assert cs.right is True
    assert cs.a is True
    assert cs.b is True
    assert cs.start is True
    assert cs.select is True


def test_magma_hub_mock():
    bus = I2CBus(99)
    hub = MagmaHub(0x08, bus, num_controllers=1)
    assert hub.address == 0x08
    assert hub.num_controllers == 1
    assert hub._bus.is_mock is True

    states = hub.poll()
    assert len(states) == 1
    assert isinstance(states[0], ControllerState)


def test_magma_hub_input():
    bus = I2CBus(99)
    hub = MagmaHub(0x08, bus, num_controllers=1)
    inp = MagmaHubInput(hub, controller_index=0)

    state = inp.poll()
    assert state.up is False
    assert state.a is False


def test_mock_hub_is_never_connected():
    # Regression: poll() used to set connected=True on a mock bus, because a
    # failed read was indistinguishable from an all-zero controller report.
    bus = I2CBus(99)
    hub = MagmaHub(0x08, bus, num_controllers=1)
    assert hub.connected is False
    hub.poll()
    assert hub.connected is False


def test_multi_controller_connected_is_not_last_write_wins():
    bus = I2CBus(99)
    hub = MagmaHub(0x08, bus, num_controllers=4)
    hub.poll()
    assert hub.connected is False
    assert len(hub.poll()) == 4


def test_composite_input_fallback():
    bus = I2CBus(99)
    hub = MagmaHub(0x08, bus, num_controllers=1)
    hub_input = MagmaHubInput(hub)

    # Mock hub is never "connected"
    composite = CompositeInput(None, hub_input)
    assert composite.active_source == "none"
    # poll() should not crash even with keyboard=None
    state = composite.poll()
    assert state.up is False


def test_dead_hub_does_not_swallow_keyboard_input():
    # Regression: a hub on a mock/dead bus reported connected, so CompositeInput
    # latched onto it and the keyboard stopped reaching the game entirely.
    class FakeKeyboard:
        def poll(self):
            return InputState(right=True)

        def is_pressed(self, button):
            return button == "right"

    bus = I2CBus(99)
    hub = MagmaHub(0x08, bus, num_controllers=1)
    composite = CompositeInput(FakeKeyboard(), MagmaHubInput(hub))

    hub.poll()  # the poll that used to flip connected to True
    assert composite.active_source == "keyboard"
    assert composite.poll().right is True
    assert composite.is_pressed("right") is True


def test_composite_input_no_hub():
    composite = CompositeInput(None, None)
    assert composite.active_source == "none"
    state = composite.poll()
    assert state.up is False
    assert composite.is_pressed("a") is False
