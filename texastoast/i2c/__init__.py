from texastoast.i2c.bus import I2CBus
from texastoast.i2c.hub import MagmaHub
from texastoast.i2c.protocol import (
    BUTTONS_ADDR,
    CONTROLLER_SIZE,
    JOYSTICK_ADDR,
    ControllerState,
)

__all__ = [
    "I2CBus",
    "MagmaHub",
    "ControllerState",
    # Protocol constants are re-exported so callers can address the hub
    # without reaching into texastoast.i2c.protocol.
    "CONTROLLER_SIZE",
    "BUTTONS_ADDR",
    "JOYSTICK_ADDR",
]
