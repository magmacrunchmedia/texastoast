from texastoast.core.config import Config
from texastoast.core.scheduler import ManualScheduler, Scheduler

__all__ = ["Config", "GameLoop", "Game", "ManualScheduler", "Scheduler",
           "TuiGame", "GameSurface", "TuiInput", "TextualScheduler", "TuiHost"]

#: Terminal host classes. Kept behind __getattr__ because this module is
#: imported by everything and tui_game is the one place Textual is imported —
#: eager import here would make the `tui` extra a hard dependency.
_TUI_NAMES = {"TuiGame", "GameSurface", "TuiInput", "TextualScheduler"}
_HOST_NAMES = {"TuiHost"}


def __getattr__(name):
    if name == "GameLoop":
        from texastoast.core.loop import GameLoop
        return GameLoop
    if name == "Game":
        from texastoast.core.game import Game
        return Game
    if name in _HOST_NAMES:
        try:
            from texastoast.core import tui_host
        except ImportError as exc:  # pragma: no cover - depends on install
            raise ImportError(
                f"{name} needs the terminal backend. Install it with: "
                'pip install "texastoast[tui]"'
            ) from exc
        return getattr(tui_host, name)

    if name in _TUI_NAMES:
        try:
            from texastoast.core import tui_game
        except ImportError as exc:  # pragma: no cover - depends on install
            raise ImportError(
                f"{name} needs the terminal backend. Install it with: "
                'pip install "texastoast[tui]"'
            ) from exc
        return getattr(tui_game, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
