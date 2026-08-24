"""Background poller tests. All headless — the sim is the hardware."""
import time

from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.poller import HubPoller, scan_buses_async
from texastoast.i2c.protocol import BTN_A
from texastoast.i2c.sim import SimBus, simulated_hub
from texastoast.input.magma_hub import MagmaHubInput


def _wait_for(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return predicate()


def test_poller_start_stop():
    hub, _ = simulated_hub()
    poller = HubPoller(hub, poll_interval=0.005).start()
    assert poller.running is True
    poller.stop()
    assert poller.running is False
    # Safe to stop twice.
    poller.stop()


def test_poller_snapshot_reaches_main_thread():
    hub, sim = simulated_hub()
    poller = HubPoller(hub, poll_interval=0.005).start()
    try:
        sim.press(BTN_A)
        assert _wait_for(lambda: poller.get_controller(0).a)
        assert poller.connected is True

        sim.release(BTN_A)
        assert _wait_for(lambda: not poller.get_controller(0).a)
    finally:
        poller.stop()


def test_poller_poll_never_blocks_on_a_slow_bus():
    """The reason the poller exists: a stalled wire must not stall a frame."""
    hub, sim = simulated_hub()
    poller = HubPoller(hub, poll_interval=0.005).start()
    try:
        assert _wait_for(lambda: poller.connected)
        sim.set_read_delay(0.25)
        time.sleep(0.05)  # let the polling thread enter the slow read

        started = time.monotonic()
        for _ in range(50):
            poller.poll()
        elapsed = time.monotonic() - started
        assert elapsed < 0.2, f"poll() blocked for {elapsed:.3f}s"
    finally:
        sim.set_read_delay(0.0)
        poller.stop()


def test_poller_duck_types_as_a_hub_for_input():
    hub, sim = simulated_hub()
    poller = HubPoller(hub, poll_interval=0.005).start()
    try:
        inp = MagmaHubInput(poller)
        sim.press(BTN_A)
        assert _wait_for(lambda: inp.poll().a)
        assert inp.connected is True
        assert poller.stats.poll_count > 0
        assert poller.address == 0x08
        assert poller.num_controllers == 1
    finally:
        poller.stop()


def test_scan_buses_async_reports_from_its_thread():
    results = []
    thread = scan_buses_async(results.append, bus_numbers=[99])
    thread.join(timeout=5.0)
    assert not thread.is_alive()
    # Bus 99 is mock everywhere — the callback still fires, with no hubs.
    assert results == [[]]


def test_scan_buses_sync_with_sim_buses():
    sim = SimBus({0x09: 1})
    bus = I2CBus(backend=sim)
    hubs = MagmaHub.scan_buses(buses=[bus])
    assert len(hubs) == 1
    assert hubs[0].address == 0x09
