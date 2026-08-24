from texastoast.input.abstract import InputSource, InputState

__all__ = [
    "InputState", "InputSource", "KeyboardInput", "MagmaHubInput",
    "CompositeInput", "InputRecorder", "ReplayInput",
    "encode_buttons", "decode_buttons",
]


def __getattr__(name):
    if name == "KeyboardInput":
        from texastoast.input.keyboard import KeyboardInput
        return KeyboardInput
    if name == "MagmaHubInput":
        from texastoast.input.magma_hub import MagmaHubInput
        return MagmaHubInput
    if name == "CompositeInput":
        from texastoast.input.magma_hub import CompositeInput
        return CompositeInput
    if name in ("InputRecorder", "ReplayInput", "encode_buttons", "decode_buttons"):
        from texastoast.input import recording
        return getattr(recording, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
