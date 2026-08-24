"""Audio tests — all headless, no sound device touched.

The FakeBackend records every call; the Mixer's whole contract is that it
routes correctly when a backend exists and degrades to silence when it
doesn't, without ever raising into the game loop.
"""
import sys

import pytest

from texastoast.audio import Mixer, NullBackend, detect_backend
from texastoast.audio import backends as backends_mod


class FakeBackend:
    name = "fake"

    def __init__(self):
        self.calls = []
        self._next_handle = 0

    def play(self, path, *, loop=False, volume=1.0):
        self._next_handle += 1
        self.calls.append(("play", path, loop, round(volume, 4),
                           self._next_handle))
        return self._next_handle

    def stop(self, handle):
        self.calls.append(("stop", handle))

    def stop_all(self):
        self.calls.append(("stop_all",))

    def set_volume(self, handle, volume):
        self.calls.append(("set_volume", handle, round(volume, 4)))

    def close(self):
        self.calls.append(("close",))


@pytest.fixture
def wav(tmp_path):
    # Content is irrelevant — the mixer only checks existence.
    p = tmp_path / "beep.wav"
    p.write_bytes(b"RIFF")
    return p


def test_play_routes_with_effective_volume(wav):
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    mixer.load("beep", wav, volume=0.5)
    mixer.set_master_volume(0.8)

    mixer.play("beep", volume=0.5)
    op, path, loop, volume, _ = backend.calls[-1]
    assert (op, loop) == ("play", False)
    assert path == str(wav)
    assert volume == round(0.8 * 0.5 * 0.5, 4)


def test_play_music_loops_and_replaces_previous(wav):
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    mixer.load("theme", wav)
    mixer.load("boss", wav)

    mixer.play_music("theme")
    first_handle = backend.calls[-1][-1]
    assert backend.calls[-1][2] is True   # loop

    mixer.play_music("boss")
    assert ("stop", first_handle) in backend.calls


def test_stop_music_and_stop_all(wav):
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    mixer.load("theme", wav)
    mixer.play_music("theme")
    mixer.stop_music()
    assert backend.calls[-1][0] == "stop"

    mixer.stop_all()
    assert backend.calls[-1] == ("stop_all",)


def test_master_volume_reaches_current_music(wav):
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    mixer.load("theme", wav, volume=0.5)
    mixer.play_music("theme")
    handle = backend.calls[-1][-1]

    mixer.set_master_volume(0.5)
    assert ("set_volume", handle, 0.25) in backend.calls


def test_volume_clamped():
    mixer = Mixer(backend=FakeBackend())
    mixer.set_master_volume(3.0)
    assert mixer.master_volume == 1.0
    mixer.set_master_volume(-1.0)
    assert mixer.master_volume == 0.0


def test_close_stops_and_closes(wav):
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    mixer.close()
    assert ("stop_all",) in backend.calls
    assert ("close",) in backend.calls
    mixer.close()   # safe to call twice


# ── degradation ─────────────────────────────────────────────────────

def test_unknown_name_is_a_noop():
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    assert mixer.play("nope") is None
    mixer.play_music("nope")
    plays = [c for c in backend.calls if c[0] == "play"]
    assert plays == []


def test_missing_file_registers_unplayable(tmp_path):
    # Regression rationale: a Pi image missing one asset must not kill the
    # game — load warns, play is silent.
    backend = FakeBackend()
    mixer = Mixer(backend=backend)
    mixer.load("ghost", tmp_path / "missing.wav")
    assert mixer.play("ghost") is None
    assert [c for c in backend.calls if c[0] == "play"] == []


def test_null_backend_full_api_never_raises(wav):
    mixer = Mixer(backend=NullBackend())
    mixer.load("beep", wav)
    mixer.play("beep")
    mixer.play_music("beep")
    mixer.set_master_volume(0.5)
    mixer.stop_music()
    mixer.stop_all()
    mixer.close()
    assert mixer.backend_name == "null"


def test_raising_backend_is_swallowed(wav):
    # Regression name: a dead audio device must never kill a frame.
    class DyingBackend(FakeBackend):
        def play(self, path, *, loop=False, volume=1.0):
            raise OSError("device gone")

        def stop(self, handle):
            raise OSError("device gone")

        def stop_all(self):
            raise OSError("device gone")

    mixer = Mixer(backend=DyingBackend())
    mixer.load("beep", wav)
    assert mixer.play("beep") is None
    mixer.play_music("beep")
    mixer.stop_music()
    mixer.stop_all()
    mixer.close()


# ── detection ───────────────────────────────────────────────────────

def test_detect_falls_back_to_null(monkeypatch):
    monkeypatch.setattr(backends_mod, "PygameBackend",
                        _raiser(ImportError("no pygame")))
    monkeypatch.setattr(backends_mod.sys, "platform", "unknownos")
    monkeypatch.setattr(backends_mod.shutil, "which", lambda cmd: None)
    assert detect_backend().name == "null"


def test_detect_prefers_pygame_when_importable(monkeypatch):
    class FakePygame(FakeBackend):
        name = "pygame"

    monkeypatch.setattr(backends_mod, "PygameBackend", FakePygame)
    assert detect_backend().name == "pygame"


def test_detect_finds_command_player(monkeypatch):
    monkeypatch.setattr(backends_mod, "PygameBackend",
                        _raiser(ImportError("no pygame")))
    monkeypatch.setattr(backends_mod.sys, "platform", "linux")
    monkeypatch.setattr(backends_mod.shutil, "which",
                        lambda cmd: "/usr/bin/aplay" if cmd == "aplay" else None)
    assert detect_backend().name == "aplay"


def _raiser(exc):
    class Boom:
        def __init__(self):
            raise exc
    return Boom


# ── import hygiene ──────────────────────────────────────────────────

def test_importing_audio_does_not_import_pygame():
    # The extra must stay optional in cost as well as in packaging.
    import subprocess
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys; import texastoast.audio; from texastoast import Mixer; "
         "assert 'pygame' not in sys.modules, 'pygame leaked'"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
