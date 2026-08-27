"""The scheduling seam between :class:`~texastoast.core.loop.GameLoop` and its host.

``GameLoop`` drives itself by re-arming a one-shot timer at the end of every
tick. That is the *only* thing it needs from the outside world — two methods,
``after`` and ``after_cancel``. It has always been that small, but the parameter
was named ``root`` and typed as a tkinter widget, so the seam was an accident of
duck-typing rather than something a second backend could be written against.

Naming it changes nothing at runtime — a ``tk.Misc`` satisfies this protocol
structurally, which is exactly why the loop worked in the first place — but it
documents the contract and lets a terminal (or SDL, or headless-test) scheduler
be checked against it.

Note the deliberately loose typing of the handle: tkinter returns an opaque
string id, Textual returns a ``Timer`` object. Neither the loop nor this
protocol cares, so long as whatever ``after`` hands back is what ``after_cancel``
is later given.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Scheduler(Protocol):
    """Schedules a one-shot callback, and cancels one already scheduled."""

    def after(self, ms: int, fn: Callable[[], Any]) -> Any:
        """Run ``fn`` once, roughly ``ms`` milliseconds from now.

        Returns a handle to pass to :meth:`after_cancel`. "Roughly" is the
        contract on purpose: the loop measures real elapsed time itself and
        corrects for drift, so a scheduler is not required to be precise.
        """
        ...

    def after_cancel(self, handle: Any) -> None:
        """Cancel a pending callback.

        Must tolerate a handle that has already fired or been cancelled — the
        loop calls this during teardown without tracking which case it is in.
        """
        ...


class ManualScheduler:
    """A scheduler that only advances when told to, for tests.

    Nothing schedules itself here: :meth:`run_pending` fires whatever is due,
    and :meth:`advance` moves a virtual clock. That makes a loop driven by this
    scheduler fully deterministic and instant, with no sleeping and no display.
    """

    def __init__(self) -> None:
        self._now_ms = 0.0
        self._next_id = 0
        self._pending: dict[int, tuple[float, Callable[[], Any]]] = {}

    @property
    def now_ms(self) -> float:
        return self._now_ms

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def after(self, ms: int, fn: Callable[[], Any]) -> int:
        handle = self._next_id
        self._next_id += 1
        self._pending[handle] = (self._now_ms + max(0, ms), fn)
        return handle

    def after_cancel(self, handle: Any) -> None:
        self._pending.pop(handle, None)

    def run_pending(self) -> int:
        """Fire every callback whose deadline has passed. Returns how many ran.

        Callbacks scheduled *by* a callback are left for the next call rather
        than run immediately — otherwise a loop that re-arms itself would spin
        forever inside one invocation.
        """
        due = [(h, fn) for h, (at, fn) in self._pending.items() if at <= self._now_ms]
        for handle, _ in due:
            self._pending.pop(handle, None)
        for _, fn in due:
            fn()
        return len(due)

    def advance(self, ms: float) -> int:
        """Move the clock forward and fire whatever that makes due."""
        self._now_ms += ms
        return self.run_pending()

    def tick(self, count: int = 1, step_ms: float = 1000.0) -> int:
        """Advance ``count`` times, generously, to drive a loop N frames.

        The default step is far longer than any sane frame interval so that one
        call reliably produces one tick regardless of the loop's target fps.
        """
        fired = 0
        for _ in range(count):
            fired += self.advance(step_ms)
        return fired
