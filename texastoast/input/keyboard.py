from __future__ import annotations

import tkinter as tk
from dataclasses import replace

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

        # Several keys map to the same button. Tracking which of them are down,
        # rather than a single bool, keeps the button held until the last one is
        # released — otherwise tapping 'a' would cancel a held Left arrow.
        self._held: dict[str, set[str]] = {}

        for key, button in key_map.items():
            press_seq = f"<KeyPress-{key}>"
            release_seq = f"<KeyRelease-{key}>"
            press_id = root.bind(press_seq, lambda e, k=key, b=button: self._press(k, b))
            release_id = root.bind(release_seq, lambda e, k=key, b=button: self._release(k, b))
            self._bindings.append((press_seq, press_id))
            self._bindings.append((release_seq, release_id))

    def _press(self, key: str, button: str):
        self._held.setdefault(button, set()).add(key)
        setattr(self._state, button, True)

    def _release(self, key: str, button: str):
        keys = self._held.get(button)
        if keys is not None:
            keys.discard(key)
        setattr(self._state, button, bool(keys))

    def poll(self) -> InputState:
        """A snapshot of the current button state.

        A copy, not the live object: callers keep the previous frame's state to
        detect a fresh press, which is impossible if every poll hands back the
        same instance.
        """
        return replace(self._state)

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
        self._held.clear()
        self._state = InputState()
