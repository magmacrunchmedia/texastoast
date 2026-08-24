"""Magma Hub input adapter — same InputProtocol as KeyboardInput."""

from __future__ import annotations

import logging
from typing import Optional

from texastoast.input.abstract import InputState
from texastoast.i2c.hub import MagmaHub

logger = logging.getLogger(__name__)


class MagmaHubInput:
    """Reads controller input from a Magma Hub I2C device.

    Implements the same poll()/is_pressed() interface as KeyboardInput,
    so games can swap between them seamlessly.
    """

    def __init__(self, hub: MagmaHub, controller_index: int = 0):
        self._hub = hub
        self._controller_index = controller_index
        self._state = InputState()

    @property
    def hub(self) -> MagmaHub:
        return self._hub

    @property
    def connected(self) -> bool:
        return self._hub.connected

    def poll(self) -> InputState:
        controllers = self._hub.poll()
        if self._controller_index < len(controllers):
            cs = controllers[self._controller_index]
            self._state = InputState(
                up=cs.up,
                down=cs.down,
                left=cs.left,
                right=cs.right,
                a=cs.a,
                b=cs.b,
                start=cs.start,
                select=cs.select,
            )
        return self._state

    def is_pressed(self, button: str) -> bool:
        return getattr(self._state, button, False)


class CompositeInput:
    """Combines keyboard and Magma Hub input — falls back to keyboard
    when no hub is connected."""

    def __init__(self, keyboard, hub_input: Optional[MagmaHubInput] = None):
        self._keyboard = keyboard
        self._hub_input = hub_input

    @property
    def active_source(self) -> str:
        if self._hub_input and self._hub_input.connected:
            return "magma_hub"
        return "keyboard"

    def poll(self) -> InputState:
        if self._hub_input and self._hub_input.connected:
            return self._hub_input.poll()
        return self._keyboard.poll()

    def is_pressed(self, button: str) -> bool:
        if self._hub_input and self._hub_input.connected:
            return self._hub_input.is_pressed(button)
        return self._keyboard.is_pressed(button)
