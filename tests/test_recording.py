"""Recording and replay tests — the .ttrec format round trip."""
import json

from texastoast.i2c.protocol import (
    BTN_A,
    BTN_B,
    BTN_DOWN,
    BTN_LEFT,
    BTN_RIGHT,
    BTN_SELECT,
    BTN_START,
    BTN_UP,
)
from texastoast.i2c.sim import simulated_hub
from texastoast.input.abstract import InputState
from texastoast.input.magma_hub import MagmaHubInput
from texastoast.input.recording import (
    InputRecorder,
    ReplayInput,
    decode_buttons,
    encode_buttons,
    load_events,
)


class ScriptedSource:
    """An InputSource returning a queued sequence of states."""

    def __init__(self, states):
        self._states = list(states)
        self._current = InputState()

    def poll(self):
        if self._states:
            self._current = self._states.pop(0)
        return self._current

    def is_pressed(self, button):
        return getattr(self._current, button, False)


def test_encode_decode_round_trips_every_button():
    for name, mask in [("up", BTN_UP), ("down", BTN_DOWN), ("left", BTN_LEFT),
                       ("right", BTN_RIGHT), ("a", BTN_A), ("b", BTN_B),
                       ("start", BTN_START), ("select", BTN_SELECT)]:
        state = InputState(**{name: True})
        assert encode_buttons(state) == mask
        assert decode_buttons(mask) == state


def test_idle_session_records_no_events(tmp_path):
    path = tmp_path / "idle.ttrec"
    recorder = InputRecorder(ScriptedSource([InputState()] * 5), path)
    recorder.start()
    for _ in range(5):
        recorder.poll()
    recorder.stop()

    lines = path.read_text().splitlines()
    assert len(lines) == 1  # header only
    header = json.loads(lines[0])
    assert header["format"] == "ttrec"
    assert header["version"] == 1


def test_recorder_writes_deltas_only(tmp_path):
    path = tmp_path / "session.ttrec"
    states = [
        InputState(),
        InputState(a=True),
        InputState(a=True),   # unchanged — no line
        InputState(a=True, up=True),
        InputState(),
    ]
    recorder = InputRecorder(ScriptedSource(states), path)
    recorder.start()
    for _ in states:
        recorder.poll()
    recorder.stop()

    events = load_events(path)
    assert [e["buttons"] for e in events] == [BTN_A, BTN_A | BTN_UP, 0]


def test_recorder_is_transparent():
    source = ScriptedSource([InputState(right=True)])
    recorder = InputRecorder(source)
    recorder.start()
    assert recorder.poll().right is True
    assert recorder.is_pressed("right") is True
    recorder.stop()


def test_recorder_save_in_memory(tmp_path):
    recorder = InputRecorder(ScriptedSource([InputState(b=True)]))
    recorder.start()
    recorder.poll()
    recorder.stop()
    assert [e["buttons"] for e in recorder.events] == [BTN_B]

    path = tmp_path / "saved.ttrec"
    recorder.save(path)
    assert [e["buttons"] for e in load_events(path)] == [BTN_B]


def _sample_events():
    return [
        {"t": 0.1, "buttons": BTN_A},
        {"t": 0.3, "buttons": BTN_A | BTN_UP},
        {"t": 0.5, "buttons": 0},
    ]


def test_replay_is_deterministic():
    """Two manual runs with the same advance() calls see the same states."""
    runs = []
    for _ in range(2):
        replay = ReplayInput(_sample_events())
        seen = []
        for _ in range(12):
            replay.advance(0.05)
            seen.append(encode_buttons(replay.poll()))
        runs.append(seen)
    assert runs[0] == runs[1]
    assert BTN_A in runs[0]
    assert (BTN_A | BTN_UP) in runs[0]
    assert runs[0][-1] == 0


def test_replay_holds_last_state_and_finishes():
    replay = ReplayInput([{"t": 0.1, "buttons": BTN_A}])
    replay.advance(1.0)
    assert replay.poll().a is True
    assert replay.finished is True
    replay.advance(1.0)
    assert replay.poll().a is True


def test_replay_seek_backward_replays_from_the_top():
    replay = ReplayInput(_sample_events())
    replay.seek(0.4)
    assert replay.poll().up is True
    replay.seek(0.15)
    state = replay.poll()
    assert state.a is True
    assert state.up is False


def test_replay_loop_wraps():
    replay = ReplayInput([{"t": 0.1, "buttons": BTN_A}, {"t": 0.2, "buttons": 0}],
                         loop=True)
    replay.advance(0.15)   # inside the first pass: A held
    assert replay.poll().a is True
    replay.advance(0.2)    # 0.35 → wrapped to 0.15: A held again
    assert replay.poll().a is True
    assert replay.finished is False


def test_replay_through_the_full_hardware_stack(tmp_path):
    """A recorded session, fed into the sim, reproduces the same InputStates
    out of the real MagmaHub + MagmaHubInput chain."""
    path = tmp_path / "fw.ttrec"
    path.write_text(
        json.dumps({"format": "ttrec", "version": 1}) + "\n"
        + json.dumps({"t": 0.1, "buttons": BTN_A}) + "\n"
        + json.dumps({"t": 0.3, "buttons": 0, "joystick": 0x48}) + "\n"
    )

    hub, sim = simulated_hub()
    driver = sim.play_recording(path)
    inp = MagmaHubInput(hub)

    driver.advance(0.2)
    assert inp.poll().a is True

    driver.advance(0.2)
    state = inp.poll()
    assert state.a is False
    assert hub.get_controller(0).joystick == 0x48
    assert driver.finished is True
