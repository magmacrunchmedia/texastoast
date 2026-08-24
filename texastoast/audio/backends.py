"""Audio backends — the tiers a Mixer can sit on.

Same shape as :class:`~texastoast.i2c.bus.I2CBus`: a Protocol surface, a
detection chain, and graceful degradation all the way down to a backend that
does nothing. A game with no audio device runs identically to a game with
one, just silently.

Tiers, best first:

* **pygame** — real mixing, seamless loops, per-channel volume. Optional:
  ``pip install "texastoast[audio]"`` (pygame-ce; SDL2 is first-class on the
  Raspberry Pi). Only ``pygame.mixer`` is initialized — no window, no
  display subsystem.
* **winsound / aplay / afplay** — zero-install platform players, SFX-grade:
  winsound plays one sound at a time; the command players spawn a process
  per sound and loop by respawn (audible seam). ``set_volume`` is a no-op
  where the player has no volume flag — the method exists so games written
  against this tier upgrade cleanly, like ``present()`` on tkinter.
* **null** — every call is a silent no-op.

The guaranteed format across all tiers is **WAV**. The pygame tier happens to
decode OGG too; that is allowed but not promised.

pygame is imported only inside ``PygameBackend`` — importing this module (or
``texastoast``) never pulls it in.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
import threading
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class AudioBackend(Protocol):
    """Structural contract — a backend is anything with this surface."""

    name: str

    def play(self, path: str, *, loop: bool = False,
             volume: float = 1.0) -> object | None: ...

    def stop(self, handle: object) -> None: ...

    def stop_all(self) -> None: ...

    def set_volume(self, handle: object, volume: float) -> None: ...

    def close(self) -> None: ...


class PygameBackend:
    """pygame-ce's mixer. Raises at construction if pygame is unavailable or
    the mixer cannot initialize — detection catches that and moves on."""

    name = "pygame"

    def __init__(self):
        import pygame  # lazy: only this backend pays for it

        self._pygame = pygame
        pygame.mixer.init()
        self._sounds: dict[str, object] = {}

    def play(self, path, *, loop=False, volume=1.0):
        sound = self._sounds.get(path)
        if sound is None:
            sound = self._pygame.mixer.Sound(path)
            self._sounds[path] = sound
        channel = sound.play(loops=-1 if loop else 0)
        if channel is not None:
            channel.set_volume(volume)
        return channel

    def stop(self, handle):
        if handle is not None:
            handle.stop()

    def stop_all(self):
        self._pygame.mixer.stop()

    def set_volume(self, handle, volume):
        if handle is not None:
            handle.set_volume(volume)

    def close(self):
        try:
            self._pygame.mixer.quit()
        except Exception:
            pass


class WinsoundBackend:
    """Windows' built-in player. One sound at a time — a new play cancels the
    previous — which makes it honest SFX-grade, not a mixer."""

    name = "winsound"

    def __init__(self):
        import winsound

        self._winsound = winsound

    def play(self, path, *, loop=False, volume=1.0):
        flags = self._winsound.SND_FILENAME | self._winsound.SND_ASYNC
        if loop:
            flags |= self._winsound.SND_LOOP
        self._winsound.PlaySound(path, flags)
        return path  # the handle is nominal: stopping anything stops everything

    def stop(self, handle):
        self.stop_all()

    def stop_all(self):
        self._winsound.PlaySound(None, 0)

    def set_volume(self, handle, volume):
        pass  # winsound has no volume control — documented no-op

    def close(self):
        self.stop_all()


class CommandBackend:
    """A command-line player (``aplay`` on Linux/Pi, ``afplay`` on macOS).

    One process per sound; the system mixer mixes them (ALSA dmix on the Pi).
    Loop is a respawn thread — same daemon-thread shape as HubPoller — with
    an audible seam between repeats.
    """

    def __init__(self, command: str):
        self.name = command
        self._command = command
        self._procs: list = []
        self._loops: list[threading.Event] = []
        self._lock = threading.Lock()

    def _spawn(self, path, volume):
        args = [self._command]
        if self._command == "afplay":
            args += ["-v", str(volume)]
        args.append(path)
        return subprocess.Popen(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def play(self, path, *, loop=False, volume=1.0):
        if not loop:
            proc = self._spawn(path, volume)
            with self._lock:
                self._procs = [p for p in self._procs if p.poll() is None]
                self._procs.append(proc)
            return proc

        stop_event = threading.Event()

        def _run():
            while not stop_event.is_set():
                proc = self._spawn(path, volume)
                with self._lock:
                    self._procs.append(proc)
                proc.wait()

        thread = threading.Thread(target=_run, name=f"audio-loop-{path}",
                                  daemon=True)
        thread.start()
        with self._lock:
            self._loops.append(stop_event)
        return stop_event  # the handle for a loop is its stop event

    def stop(self, handle):
        if isinstance(handle, threading.Event):
            handle.set()
        if hasattr(handle, "terminate"):
            try:
                handle.terminate()
            except Exception:
                pass
        # A looping handle's current process dies with stop_all or naturally.

    def stop_all(self):
        with self._lock:
            for event in self._loops:
                event.set()
            self._loops.clear()
            for proc in self._procs:
                try:
                    proc.terminate()
                except Exception:
                    pass
            self._procs.clear()

    def set_volume(self, handle, volume):
        pass  # applied at spawn for afplay; aplay has no volume flag

    def close(self):
        self.stop_all()


class NullBackend:
    """No audio at all. Every call is a silent no-op — the mock-I2CBus of
    sound, so a game runs identically on a machine with no audio path."""

    name = "null"

    def play(self, path, *, loop=False, volume=1.0):
        return None

    def stop(self, handle):
        pass

    def stop_all(self):
        pass

    def set_volume(self, handle, volume):
        pass

    def close(self):
        pass


def detect_backend() -> AudioBackend:
    """The best backend this machine offers, never raising."""
    try:
        backend = PygameBackend()
        logger.info("Audio: pygame mixer")
        return backend
    except Exception as e:
        logger.debug(f"Audio: pygame unavailable ({e})")

    if sys.platform == "win32":
        try:
            backend = WinsoundBackend()
            logger.info("Audio: winsound (SFX-grade — one sound at a time)")
            return backend
        except Exception as e:
            logger.debug(f"Audio: winsound unavailable ({e})")

    for command in ("aplay", "afplay"):
        if shutil.which(command):
            logger.info(f"Audio: {command} (SFX-grade — process per sound)")
            return CommandBackend(command)

    logger.info("Audio: no backend found — running silent")
    return NullBackend()
