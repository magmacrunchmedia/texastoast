"""Hub simulator tests.

The point of the bus-level fake: every test here runs the *real* MagmaHub
protocol code — select-write, block read, connected latching, ControllerState
parsing — with no I2C hardware, no smbus2, and no display.
"""
import pytest

from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.protocol import (
    BTN_A,
    BTN_START,
    BTN_UP,
    CONTROLLER_SIZE,
    ControllerState,
)
from texastoast.i2c.sim import SimBus, simulated_hub


def test_injected_backend_is_not_mock():
    bus = I2CBus(backend=SimBus())
    assert bus.is_mock is False
    bus.close()


def test_block_read_requires_select_write():
    """The firmware handshake, enforced.

    A sim that answered any read would keep passing even if MagmaHub stopped
    sending the select-write — this is the regression the strictness catches.
    """
    sim = SimBus()
    with pytest.raises(OSError):
        sim.read_i2c_block_data(0x08, 0x00, CONTROLLER_SIZE)

    # After the select-write the same read succeeds — once.
    sim.write_i2c_block_data(0x08, 0x00, [CONTROLLER_SIZE])
    assert sim.read_i2c_block_data(0x08, 0x00, CONTROLLER_SIZE) == [0, 0]
    with pytest.raises(OSError):
        sim.read_i2c_block_data(0x08, 0x00, CONTROLLER_SIZE)


def test_absent_address_raises():
    sim = SimBus({0x08: 1})
    with pytest.raises(OSError):
        sim.read_byte(0x09)


def test_full_stack_round_trip():
    """Buttons set on the sim come out of the real MagmaHub.poll()."""
    hub, sim = simulated_hub()
    assert hub.connected is False

    sim.press(BTN_UP | BTN_A)
    states = hub.poll()
    assert hub.connected is True
    assert states[0].up is True
    assert states[0].a is True
    assert states[0].down is False

    sim.release(BTN_UP)
    states = hub.poll()
    assert states[0].up is False
    assert states[0].a is True


def test_set_controller_and_joystick():
    hub, sim = simulated_hub()
    sim.set_controller(0x08, 0, ControllerState(buttons=BTN_START, joystick=0x84))
    state = hub.poll()[0]
    assert state.start is True
    assert state.joystick == 0x84


def test_multi_controller_memory_is_separate():
    hub, sim = simulated_hub(num_controllers=2)
    sim.press(BTN_A, index=1)
    states = hub.poll()
    assert states[0].a is False
    assert states[1].a is True


def test_error_injection_counts_errors():
    hub, sim = simulated_hub()
    hub.poll()
    assert hub.stats.error_count == 0

    sim.fail_next_reads(1)
    hub.poll()
    assert hub.stats.error_count == 1
    # And it recovers once the injected failures are spent.
    hub.poll()
    assert hub.connected is True


def test_disconnect_and_reconnect():
    hub, sim = simulated_hub()
    hub.poll()
    assert hub.connected is True

    sim.disconnect_hub(0x08)
    hub.poll()
    assert hub.connected is False

    sim.reconnect_hub(0x08)
    hub.poll()
    assert hub.connected is True


def test_probe_and_scan_against_sim():
    sim = SimBus({0x08: 1, 0x0A: 1})
    bus = I2CBus(backend=sim)
    assert bus.probe(0x08) is True
    assert bus.probe(0x09) is False
    assert bus.scan(start=0x03, end=0x10) == [0x08, 0x0A]


def test_scan_buses_finds_sim_hubs():
    sim = SimBus({0x08: 1, 0x0A: 1})
    bus = I2CBus(backend=sim)
    hubs = MagmaHub.scan_buses(buses=[bus])
    assert sorted(h.address for h in hubs) == [0x08, 0x0A]


def test_scan_buses_probes_only_candidate_addresses():
    """The old scan swept 117 addresses on the game's startup path."""
    probes = []

    class CountingSim(SimBus):
        def read_byte(self, address):
            probes.append(address)
            return super().read_byte(address)

    bus = I2CBus(backend=CountingSim({0x08: 1}))
    MagmaHub.scan_buses(buses=[bus])
    assert len(probes) == 4  # DEFAULT_HUB_ADDRESSES, nothing more
