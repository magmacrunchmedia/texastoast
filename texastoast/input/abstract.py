from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class InputState:
    """Unified controller state for all input methods."""
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    a: bool = False
    b: bool = False
    start: bool = False
    select: bool = False

    @property
    def dx(self) -> float:
        result = 0.0
        if self.left:
            result -= 1.0
        if self.right:
            result += 1.0
        return result

    @property
    def dy(self) -> float:
        result = 0.0
        if self.up:
            result -= 1.0
        if self.down:
            result += 1.0
        return result

    def is_any_direction(self) -> bool:
        return self.up or self.down or self.left or self.right


class InputSource(Protocol):
    """Protocol for all input backends (keyboard, Magma Hub, etc.)."""
    def poll(self) -> InputState: ...
    def is_pressed(self, button: str) -> bool: ...
