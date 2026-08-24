"""Game loop tests. The loop drives itself via tkinter's after(), so these
pump the event loop by hand rather than calling mainloop()."""
import time

from conftest import requires_tk

from texastoast.core.loop import GameLoop

pytestmark = requires_tk


def _pump(root, seconds):
    """Run the tk event loop for a wall-clock duration."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        root.update()
        time.sleep(0.001)


def test_loop_calls_update_and_render(tk_root):
    calls = {"update": 0, "render": 0}
    loop = GameLoop(tk_root, lambda dt: calls.__setitem__("update", calls["update"] + 1),
                    lambda: calls.__setitem__("render", calls["render"] + 1), fps=60)
    loop.start()
    _pump(tk_root, 0.2)
    loop.stop()
    assert calls["update"] > 1
    assert calls["render"] > 1


def test_loop_dt_is_clamped(tk_root):
    seen = []
    loop = GameLoop(tk_root, seen.append, lambda: None, fps=60)
    loop.start()
    # Simulate a long stall (a dragged window, a breakpoint) before the tick.
    loop._last_time = time.monotonic() - 5.0
    tk_root.update()
    loop.stop()
    assert seen
    assert max(seen) <= GameLoop.MAX_DT


def test_loop_survives_a_transient_exception_in_update(tk_root):
    rendered = []
    ticks = []

    def flaky(dt):
        ticks.append(dt)
        if len(ticks) == 1:
            raise ValueError("kaboom")

    loop = GameLoop(tk_root, flaky, lambda: rendered.append(1), fps=60)
    loop.start()
    _pump(tk_root, 0.15)
    still_running = loop._running
    loop.stop()
    # A one-off failure is logged, not propagated, and the loop keeps ticking.
    assert still_running
    assert len(ticks) > 1
    assert rendered


def test_loop_stops_and_reraises_after_persistent_errors(tk_root):
    def boom(dt):
        raise ValueError("kaboom")

    seen = []
    loop = GameLoop(tk_root, boom, lambda: None, fps=60,
                    max_consecutive_errors=3, on_error=seen.append)
    loop.start()
    _pump(tk_root, 0.3)
    # A loop that logged and carried on would spray tracebacks forever while
    # the game looked alive; past the threshold it must stop and hand the real
    # error to its owner.
    assert not loop._running
    assert isinstance(loop.error, ValueError)
    assert [type(e) for e in seen] == [ValueError]
    loop.stop()


def test_error_count_resets_after_a_good_frame(tk_root):
    ticks = []

    def every_other(dt):
        ticks.append(dt)
        if len(ticks) % 2:
            raise ValueError("kaboom")

    loop = GameLoop(tk_root, every_other, lambda: None, fps=120, max_consecutive_errors=3)
    loop.start()
    _pump(tk_root, 0.2)
    still_running = loop._running
    loop.stop()
    # Failures are only fatal when consecutive.
    assert still_running
    assert len(ticks) > 6


def test_stop_is_idempotent_and_halts_ticking(tk_root):
    calls = []
    loop = GameLoop(tk_root, calls.append, lambda: None, fps=60)
    loop.start()
    _pump(tk_root, 0.1)
    loop.stop()
    loop.stop()  # must not raise
    count = len(calls)
    _pump(tk_root, 0.1)
    assert len(calls) == count


def test_start_is_idempotent(tk_root):
    loop = GameLoop(tk_root, lambda dt: None, lambda: None, fps=60)
    loop.start()
    first = loop._after_id
    loop.start()  # second start must not schedule a competing tick chain
    assert loop._after_id == first
    loop.stop()


def test_stop_from_inside_update_does_not_reschedule(tk_root):
    calls = []

    def update(dt):
        calls.append(dt)
        loop.stop()

    loop = GameLoop(tk_root, update, lambda: None, fps=60)
    loop.start()
    _pump(tk_root, 0.15)
    assert len(calls) == 1
    assert loop._after_id is None


def test_frame_interval_accounts_for_work_time(tk_root):
    # Regression: after() was called with the full interval regardless of how
    # long update/render took, so every frame cost interval + work and the
    # target fps was unreachable. Assert on the scheduled delay rather than on
    # wall-clock frame counts, which are too flaky to gate CI on.
    delays = []

    def recording_after(ms, func=None):
        delays.append(ms)
        return "after#stub"

    loop = GameLoop(tk_root, lambda dt: time.sleep(0.015), lambda: None, fps=30)
    assert loop._interval_ms == 33

    loop._running = True
    loop._last_time = time.monotonic()
    loop._fps_timer = loop._last_time
    loop._root = type("R", (), {"after": staticmethod(recording_after)})()
    loop._tick()

    assert delays, "tick should schedule the next frame"
    # ~15ms of work out of a 33ms budget leaves roughly 18ms.
    assert delays[0] < 33
    assert delays[0] >= 1


def test_frame_delay_never_drops_below_one_ms(tk_root):
    # Work longer than the whole frame budget must still schedule, not pass a
    # zero or negative delay to after().
    delays = []
    loop = GameLoop(tk_root, lambda dt: time.sleep(0.05), lambda: None, fps=60)
    loop._running = True
    loop._last_time = time.monotonic()
    loop._fps_timer = loop._last_time
    loop._root = type("R", (), {"after": staticmethod(lambda ms, f=None: delays.append(ms))})()
    loop._tick()
    assert delays == [1]


def test_quitting_from_update_skips_that_frame_s_render(tk_root):
    rendered = []

    def update(dt):
        loop.stop()

    loop = GameLoop(tk_root, update, lambda: rendered.append(1), fps=60)
    loop.start()
    _pump(tk_root, 0.1)
    loop.stop()
    # Rendering after a quit draws onto a canvas that may already be destroyed.
    assert rendered == []
