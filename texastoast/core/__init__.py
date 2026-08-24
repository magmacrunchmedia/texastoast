from texastoast.core.config import Config

__all__ = ["Config", "GameLoop", "Game"]


def __getattr__(name):
    if name == "GameLoop":
        from texastoast.core.loop import GameLoop
        return GameLoop
    if name == "Game":
        from texastoast.core.game import Game
        return Game
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
