from __future__ import annotations

import logging
import time
from collections.abc import Callable

from texastoast.core.scheduler import Scheduler

logger = logging.getLogger(__name__)


class GameLoop:
    """Tick-based game loop, driven by a :class:`~texastoast.core.scheduler.Scheduler`.

    The loop re-arms a one-shot timer at the end of every tick, so the only
    thing it needs from its host is ``after``/``after_cancel``. A tkinter root
    satisfies that structurally, which is what the parameter used to be typed
    as; naming the protocol lets a terminal or headless scheduler be supplied
    just as well.
    """

    MAX_DT = 0.1  # clamp dt to prevent physics explosions on large gaps

    def __init__(
        self,
        scheduler: Scheduler,
        update_fn: Callable[[float], None],
        render_fn: Callable[[], None],
        fps: int = 30,
        max_consecutive_errors: int = 10,
        on_error: Callable[[BaseException], None] | None = None,
    ):
        self._scheduler = scheduler
        self._update_fn = update_fn
        self._render_fn = render_fn
        self._interval_ms = max(1, int(1000 / fps))
        self._max_consecutive_errors = max_consecutive_errors
        self._on_error = on_error
        self._consecutive_errors = 0
        self._error: BaseException | None = None
        self._running = False
        self._last_time = 0.0
        self._frame_count = 0
        self._fps_display = 0.0
        self._fps_timer = 0.0
        self._after_id = None

    @property
    def scheduler(self) -> Scheduler:
        return self._scheduler

    @property
    def fps(self) -> float:
        return self._fps_display

    @property
    def error(self) -> BaseException | None:
        """The exception that stopped the loop, if one did."""
        return self._error

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def start(self):
        if self._running:
            return
        self._running = True
        self._last_time = time.monotonic()
        self._fps_timer = self._last_time
        self._frame_count = 0
        self._consecutive_errors = 0
        self._error = None
        self._tick()

    def stop(self):
        self._running = False
        if self._after_id is not None:
            try:
                self._scheduler.after_cancel(self._after_id)
            except Exception:
                # Root may already be torn down; nothing left to cancel.
                pass
            self._after_id = None

    def _tick(self):
        if not self._running:
            return

        now = time.monotonic()
        dt = min(now - self._last_time, self.MAX_DT)
        self._last_time = now

        try:
            self._update_fn(dt)
            # update() may have quit the game — a menu's Quit item, a win
            # condition, a script calling quit(). Rendering after that draws
            # onto a destroyed canvas.
            if self._running:
                self._render_fn()
        except Exception as exc:
            # A loop that logs and carries on turns one broken callback into
            # thousands of identical tracebacks a second while the game looks
            # alive but does nothing. Tolerate a transient failure; give up on
            # a persistent one.
            self._consecutive_errors += 1
            if (self._max_consecutive_errors > 0
                    and self._consecutive_errors >= self._max_consecutive_errors):
                logger.error(
                    "Stopping the game loop after %d consecutive errors",
                    self._consecutive_errors,
                )
                self._error = exc
                self.stop()
                if self._on_error is not None:
                    # The owner takes it from here — typically by ending the
                    # main loop and re-raising from start().
                    try:
                        self._on_error(exc)
                    except Exception:
                        logger.exception("Exception in game loop error handler")
                    return
                # Nothing is listening. Re-raising here may not reach the
                # caller — tkinter catches it inside the after() callback and
                # hands it to report_callback_exception — but that is what
                # prints the traceback, which beats losing it entirely.
                raise
            if self._consecutive_errors == 1:
                logger.exception("Exception in game loop update/render")
            else:
                # The same error, again. One traceback per streak is enough;
                # repeating it 30 times a second buries everything else.
                logger.error(
                    "Exception in game loop update/render (%d in a row): %r",
                    self._consecutive_errors, exc,
                )
        else:
            self._consecutive_errors = 0

        self._frame_count += 1
        if now - self._fps_timer >= 1.0:
            self._fps_display = self._frame_count / (now - self._fps_timer)
            self._frame_count = 0
            self._fps_timer = now

        if not self._running:  # stop() may have been called from update/render
            return

        # Subtract the time update/render just spent, otherwise every frame
        # costs interval + work and the target fps is never reached.
        work_ms = (time.monotonic() - now) * 1000.0
        delay = max(1, int(self._interval_ms - work_ms))
        self._after_id = self._scheduler.after(delay, self._tick)
