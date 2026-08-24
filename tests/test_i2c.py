from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.protocol import (
    ControllerState, CONTROLLER_SIZE,
    BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT,
    BTN_A, BTN_B, BTN_START, BTN_SELECT,
)
from texastoast.input.magma_hub import MagmaHubInput, CompositeInput


def test_i2cbus_mock():
    bus = I2CBus(99)
    assert bus.is_mock is True
    assert bus.read_byte_data(0x08, 0) == 0x00
    assert bus.read_i2c_block_data(0x08, 0, 2) == [0x00, 0x00]
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


def test_composite_input_no_hub():
    composite = CompositeInput(None, None)
    assert composite.active_source == "none"
    state = composite.poll()
    assert state.up is False
    assert composite.is_pressed("a") is False
