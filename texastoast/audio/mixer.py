"""The Mixer — load sounds by name, play them, never crash a frame over audio.

Every method is safe whatever the backend: a game on a machine with no audio
device runs identically to one with speakers, the way a game with no I2C bus
runs identically on a laptop. Wire teardown into the game's lifecycle::

    mixer = Mixer()
    game.on_close(mixer.close)

    mixer.load("jump", "assets/jump.wav")
    mixer.load("theme", "assets/theme.wav", volume=0.6)
    mixer.play_music("theme")
    ...
    mixer.play("jump")

WAV is the guaranteed format on every backend tier.
"""

from __future__ import annotations

import logging
from pathlib import Path

from texastoast.audio.backends import AudioBackend, detect_backend

logger = logging.getLogger(__name__)


class _Sound:
    def __init__(self, path: Path, volume: float, playable: bool):
        self.path = path
        self.volume = volume
        self.playable = playable


class Mixer:
    """A load-by-name sound registry over a swappable backend.

    ``backend`` defaults to :func:`detect_backend`; inject a fake (anything
    with the :class:`~texastoast.audio.backends.AudioBackend` surface) for
    tests, exactly like ``I2CBus(backend=...)``.

    Effective playback volume is ``master × load volume × play override``,
    computed when a sound starts.
    """

    def __init__(self, backend: AudioBackend | None = None):
        self._backend = backend if backend is not None else detect_backend()
        self._sounds: dict[str, _Sound] = {}
        self._master = 1.0
        self._music_handle: object | None = None
        self._music_name: str | None = None

    @property
    def backend_name(self) -> str:
        return self._backend.name

    @property
    def master_volume(self) -> float:
        return self._master

    def load(self, name: str, path: str | Path, volume: float = 1.0):
        """Register ``path`` under ``name``.

        A missing file logs a warning and registers as unplayable — later
        ``play(name)`` calls are no-ops. Degradation, not a crash: a Pi image
        missing one asset must not kill the game.
        """
        p = Path(path)
        playable = p.is_file()
        if not playable:
            logger.warning(f"Audio: {p} not found — '{name}' will be silent")
        self._sounds[name] = _Sound(p, self._clamp(volume), playable)

    def play(self, name: str, volume: float | None = None):
        """Fire-and-forget playback of a loaded sound. Returns the backend's
        handle, or None when nothing played."""
        sound = self._sounds.get(name)
        if sound is None:
            logger.debug(f"Audio: play of unknown sound '{name}' — no-op")
            return None
        if not sound.playable:
            return None
        effective = self._master * sound.volume * self._clamp(
            volume if volume is not None else 1.0
        )
        try:
            return self._backend.play(str(sound.path), loop=False,
                                      volume=effective)
        except Exception as e:
            # A dead audio device must never kill a frame.
            logger.debug(f"Audio: backend play failed ({e})")
            return None

    def play_music(self, name: str, loop: bool = True):
        """Play a loaded sound as music: one slot, replacing whatever music
        was playing."""
        self.stop_music()
        sound = self._sounds.get(name)
        if sound is None or not sound.playable:
            logger.debug(f"Audio: music '{name}' unavailable — no-op")
            return
        try:
            self._music_handle = self._backend.play(
                str(sound.path), loop=loop,
                volume=self._master * sound.volume,
            )
            self._music_name = name
        except Exception as e:
            logger.debug(f"Audio: backend music play failed ({e})")

    def stop_music(self):
        if self._music_handle is not None:
            try:
                self._backend.stop(self._music_handle)
            except Exception as e:
                logger.debug(f"Audio: backend stop failed ({e})")
        self._music_handle = None
        self._music_name = None

    def stop_all(self):
        """Stop everything, music included."""
        try:
            self._backend.stop_all()
        except Exception as e:
            logger.debug(f"Audio: backend stop_all failed ({e})")
        self._music_handle = None
        self._music_name = None

    def set_master_volume(self, volume: float):
        """Master volume, 0..1, applied to sounds started from now on — and
        to the current music where the backend supports live volume."""
        self._master = self._clamp(volume)
        if self._music_handle is not None and self._music_name is not None:
            sound = self._sounds.get(self._music_name)
            if sound is not None:
                try:
                    self._backend.set_volume(
                        self._music_handle, self._master * sound.volume
                    )
                except Exception as e:
                    logger.debug(f"Audio: backend set_volume failed ({e})")

    def close(self):
        """Stop everything and release the backend. Safe to call twice.
        Wire it: ``game.on_close(mixer.close)``."""
        self.stop_all()
        try:
            self._backend.close()
        except Exception as e:
            logger.debug(f"Audio: backend close failed ({e})")

    @staticmethod
    def _clamp(volume: float) -> float:
        return max(0.0, min(1.0, volume))
