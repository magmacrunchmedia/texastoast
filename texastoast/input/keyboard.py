from __future__ import annotations

import tkinter as tk

from texastoast.input.abstract import InputState


class KeyboardInput:
    """Keyboard input using tkinter key bindings."""

    def __init__(self, root: tk.Tk):
        self._state = InputState()
        self._root = root
        self._bindings: list[str] = []

        key_map = {
            "Up": "up", "w": "up", "W": "up",
            "Down": "down", "s": "down", "S": "down",
            "Left": "left", "a": "left", "A": "left",
            "Right": "right", "d": "right", "D": "right",
            "z": "a", "Z": "a", "Return": "a",
            "x": "b", "X": "b", "BackSpace": "b",
            "Escape": "start", "p": "start", "P": "start",
            "Shift_L": "select", "Shift_R": "select",
        }

        for key, button in key_map.items():
            press_id = root.bind(f"<KeyPress-{key}>", lambda e, b=button: self._set(b, True))
            release_id = root.bind(f"<KeyRelease-{key}>", lambda e, b=button: self._set(b, False))
            self._bindings.extend([press_id, release_id])

    def _set(self, button: str, value: bool):
        setattr(self._state, button, value)

    def poll(self) -> InputState:
        return self._state

    def is_pressed(self, button: str) -> bool:
        return getattr(self._state, button, False)

    def destroy(self):
        for binding_id in self._bindings:
            try:
                self._root.unbind(binding_id)
            except Exception:
                pass
        self._bindings.clear()
