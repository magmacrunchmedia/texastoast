"""Controller bench tests.

Argument parsing is headless; the app itself needs the shared Tk root and
runs against the simulator — no I2C hardware in any test.
"""
import time

from conftest import requires_tk

from texastoast.devtools.bench import BenchApp, parse_args
from texastoast.i2c.protocol import BTN_A


def test_parse_args_defaults():
    args = parse_args([])
    assert args.sim is False
    assert args.bus == 1
    assert args.addr is None
    assert args.controllers == 1
    assert args.record is None


def test_parse_args_hex_address_and_flags():
    args = parse_args(["--sim", "--addr", "0x0a", "--controllers", "2",
                       "--record", "out.ttrec"])
    assert args.sim is True
    assert args.addr == 0x0A
    assert args.controllers == 2
    assert args.record == "out.ttrec"


@requires_tk
def test_sim_mode_builds_panels_and_banner(tk_root):
    app = BenchApp(tk_root)
    try:
        app.enter_sim_mode(num_controllers=2)
        assert "SIMULATOR" in app._banner.cget("text")
        assert len(app._panels) == 1
        assert len(app._panels[0].controllers) == 2
    finally:
        app._closed = True
        for poller in app._pollers:
            poller.stop()


@requires_tk
def test_button_press_lights_the_indicator(tk_root):
    app = BenchApp(tk_root)
    try:
        app.enter_sim_mode()
        app._sim.press(BTN_A)

        # Wait for the background poller to pick the press up, then refresh.
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if app._pollers[0].get_controller(0).a:
                break
            time.sleep(0.01)
        app.refresh()

        cell = app._panels[0].controllers[0]._cells["a"]
        assert cell.cget("bg") == "#e94560"
        raw = app._panels[0].controllers[0]._raw.cget("text")
        assert "btn:0x10" in raw
    finally:
        app._closed = True
        for poller in app._pollers:
            poller.stop()


@requires_tk
def test_record_flag_wires_a_recorder(tk_root, tmp_path):
    path = tmp_path / "bench.ttrec"
    app = BenchApp(tk_root, record_path=str(path))
    try:
        app.enter_sim_mode()
        assert app._recorder is not None
        assert app._recorder.recording is True
        app.refresh()
    finally:
        app._closed = True
        for poller in app._pollers:
            poller.stop()
        app._recorder.stop()
    assert path.exists()
