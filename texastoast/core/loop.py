from __future__ import annotations

import time
from typing import Callable


class GameLoop:
    """Tick-based game loop using tkinter's after() for scheduling."""

    def __init__(
        self,
        root,
        update_fn: Callable[[float], None],
        render_fn: Callable[[], None],
        fps: int = 30,
    ):
        self._root = root
        self._update_fn = update_fn
        self._render_fn = render_fn
        self._interval_ms = max(1, int(1000 / fps))
        self._running = False
        self._last_time = 0.0
        self._frame_count = 0
        self._fps_display = 0.0
        self._fps_timer = 0.0
        self._after_id = None

    @property
    def fps(self) -> float:
        return self._fps_display

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def start(self):
        if self._running:
            return
        self._running = True
        self._last_time = time.monotonic()
        self._fps_timer = self._last_time
        self._tick()

    def stop(self):
        self._running = False
        if self._after_id is not None:
            self._root.after_cancel(self._after_id)
            self._after_id = None

    def _tick(self):
        if not self._running:
            return

        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now

        self._update_fn(dt)
        self._render_fn()

        self._frame_count += 1
        if now - self._fps_timer >= 1.0:
            self._fps_display = self._frame_count / (now - self._fps_timer)
            self._frame_count = 0
            self._fps_timer = now

        self._after_id = self._root.after(self._interval_ms, self._tick)
