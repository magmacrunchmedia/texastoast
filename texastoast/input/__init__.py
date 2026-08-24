from texastoast.input.abstract import InputState, InputSource

__all__ = ["InputState", "InputSource", "KeyboardInput", "MagmaHubInput", "CompositeInput"]


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
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
