"""Audio for texastoast games. See :mod:`texastoast.audio.mixer`.

Lazy exports: importing this package pulls in neither pygame nor any backend.
"""

__all__ = ["Mixer", "AudioBackend", "NullBackend", "detect_backend"]


def __getattr__(name):
    if name == "Mixer":
        from texastoast.audio.mixer import Mixer
        return Mixer
    if name in ("AudioBackend", "NullBackend", "detect_backend"):
        from texastoast.audio import backends
        return getattr(backends, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
