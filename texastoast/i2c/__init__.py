from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import HubStats, MagmaHub
from texastoast.i2c.protocol import (
    BUTTONS_ADDR,
    CONTROLLER_SIZE,
    JOYSTICK_ADDR,
    ControllerState,
)

__all__ = [
    "I2CBus",
    "MagmaHub",
    "HubStats",
    "ControllerState",
    # Protocol constants are re-exported so callers can address the hub
    # without reaching into texastoast.i2c.protocol.
    "CONTROLLER_SIZE",
    "BUTTONS_ADDR",
    "JOYSTICK_ADDR",
    "SimBus",
    "simulated_hub",
    "KeyboardHubDriver",
    "HubPoller",
    "scan_buses_async",
]


def __getattr__(name):
    if name in ("SimBus", "simulated_hub", "KeyboardHubDriver"):
        from texastoast.i2c import sim
        return getattr(sim, name)
    if name in ("HubPoller", "scan_buses_async"):
        from texastoast.i2c import poller
        return getattr(poller, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
