"""I2C protocol constants and controller state parsing."""

from __future__ import annotations

from dataclasses import dataclass

# ── Memory map per controller ───────────────────────────────────────

BUTTONS_ADDR = 0x00
JOYSTICK_ADDR = 0x01
CONTROLLER_SIZE = 2  # bytes per controller

# ── Button bitmasks (active high) ───────────────────────────────────

BTN_UP    = 0b00000001
BTN_DOWN  = 0b00000010
BTN_LEFT  = 0b00000100
BTN_RIGHT = 0b00001000
BTN_A     = 0b00010000
BTN_B     = 0b00100000
BTN_START = 0b01000000
BTN_SELECT = 0b10000000

# ── Default I2C addresses ───────────────────────────────────────────

DEFAULT_HUB_ADDRESSES = [0x08, 0x09, 0x0A, 0x0B]


@dataclass
class ControllerState:
    """Parsed state from one controller."""
    buttons: int = 0
    joystick: int = 0

    @property
    def up(self) -> bool:
        return bool(self.buttons & BTN_UP)

    @property
    def down(self) -> bool:
        return bool(self.buttons & BTN_DOWN)

    @property
    def left(self) -> bool:
        return bool(self.buttons & BTN_LEFT)

    @property
    def right(self) -> bool:
        return bool(self.buttons & BTN_RIGHT)

    @property
    def a(self) -> bool:
        return bool(self.buttons & BTN_A)

    @property
    def b(self) -> bool:
        return bool(self.buttons & BTN_B)

    @property
    def start(self) -> bool:
        return bool(self.buttons & BTN_START)

    @property
    def select(self) -> bool:
        return bool(self.buttons & BTN_SELECT)

    def direction(self) -> tuple[float, float]:
        dx = 0.0
        dy = 0.0
        if self.left:
            dx -= 1.0
        if self.right:
            dx += 1.0
        if self.up:
            dy -= 1.0
        if self.down:
            dy += 1.0
        return dx, dy
