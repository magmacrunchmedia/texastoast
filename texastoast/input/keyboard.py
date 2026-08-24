from __future__ import annotations

import tkinter as tk

from texastoast.input.abstract import InputState


class KeyboardInput:
    """Keyboard input using tkinter key bindings."""

    def __init__(self, root: tk.Tk):
        self._state = InputState()
        self._root = root
        # (sequence, funcid) pairs — unbind() wants the sequence, not the funcid.
        self._bindings: list[tuple[str, str]] = []

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
            press_seq = f"<KeyPress-{key}>"
            release_seq = f"<KeyRelease-{key}>"
            press_id = root.bind(press_seq, lambda e, b=button: self._set(b, True))
            release_id = root.bind(release_seq, lambda e, b=button: self._set(b, False))
            self._bindings.append((press_seq, press_id))
            self._bindings.append((release_seq, release_id))

    def _set(self, button: str, value: bool):
        setattr(self._state, button, value)

    def poll(self) -> InputState:
        return self._state

    def is_pressed(self, button: str) -> bool:
        return getattr(self._state, button, False)

    def destroy(self):
        """Remove every key binding this input source installed."""
        for sequence, funcid in self._bindings:
            try:
                self._root.unbind(sequence, funcid)
            except Exception:
                # Root may already be torn down.
                pass
        self._bindings.clear()
        self._state = InputState()
