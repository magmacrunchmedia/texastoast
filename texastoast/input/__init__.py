from texastoast.input.abstract import InputState, InputSource

__all__ = ["InputState", "InputSource", "KeyboardInput"]


def __getattr__(name):
    if name == "KeyboardInput":
        from texastoast.input.keyboard import KeyboardInput
        return KeyboardInput
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
