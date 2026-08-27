"""The Scheduler seam.

``GameLoop`` used to take a tkinter root and duck-type ``after``/``after_cancel``
off it. Naming that pair as a protocol is what lets a terminal — or these tests —
drive the loop instead. The proof is below: a fully exercised game loop with no
tkinter, no display, and no sleeping.
"""

import tkinter as tk

from texastoast.core.loop import GameLoop
from texastoast.core.scheduler import ManualScheduler, Scheduler


def test_manual_scheduler_satisfies_the_protocol():
    assert isinstance(ManualScheduler(), Scheduler)


def test_a_tkinter_root_satisfies_the_protocol():
    # Structural, so this holds without importing a display — it is why the
    # loop worked before the protocol existed, and why naming it broke nothing.
    assert isinstance(tk.Misc, type)
    assert hasattr(tk.Misc, "after")
    assert hasattr(tk.Misc, "after_cancel")


def test_callbacks_do_not_fire_before_their_deadline():
    sched = ManualScheduler()
    fired = []
    sched.after(100, lambda: fired.append(1))

    sched.advance(50)
    assert fired == []
    sched.advance(60)
    assert fired == [1]


def test_after_cancel_prevents_a_pending_callback():
    sched = ManualScheduler()
    fired = []
    handle = sched.after(10, lambda: fired.append(1))
    sched.after_cancel(handle)
    sched.advance(1000)
    assert fired == []


def test_after_cancel_tolerates_a_stale_handle():
    # The loop cancels during teardown without knowing whether it already fired.
    sched = ManualScheduler()
    handle = sched.after(0, lambda: None)
    sched.run_pending()
    sched.after_cancel(handle)
    sched.after_cancel("never-existed")


def test_a_callback_that_reschedules_does_not_spin_within_one_call():
    # Otherwise a self-re-arming loop would never return from run_pending().
    sched = ManualScheduler()
    count = []

    def again():
        count.append(1)
        sched.after(0, again)

    sched.after(0, again)
    sched.run_pending()
    assert count == [1]
    sched.run_pending()
    assert count == [1, 1]


# ── The loop, with no tkinter ────────────────────────────────────────


def _loop(sched, fps=30, **kwargs):
    updates, renders = [], []
    loop = GameLoop(sched, updates.append, lambda: renders.append(1), fps=fps, **kwargs)
    return loop, updates, renders


def test_game_loop_runs_headlessly_on_a_manual_scheduler():
    sched = ManualScheduler()
    loop, updates, renders = _loop(sched)
    loop.start()
    sched.tick(5)
    loop.stop()

    # start() ticks once immediately, then each scheduled tick adds one.
    assert len(updates) == 6
    assert len(renders) == 6
    assert loop.scheduler is sched


def test_stopping_cancels_the_pending_tick():
    sched = ManualScheduler()
    loop, updates, _ = _loop(sched)
    loop.start()
    sched.tick(2)
    loop.stop()

    assert sched.pending_count == 0
    before = len(updates)
    sched.tick(5)
    assert len(updates) == before


def test_dt_reflects_the_scheduler_not_wall_clock_only():
    sched = ManualScheduler()
    seen = []
    loop = GameLoop(sched, seen.append, lambda: None, fps=30)
    loop.start()
    sched.tick(3)
    loop.stop()
    # A virtual clock advances instantly, so real dt is ~0 but must be finite
    # and clamped — never negative, never above the guard.
    assert seen
    assert all(0 <= dt <= GameLoop.MAX_DT for dt in seen)


def test_errors_stop_the_loop_headlessly():
    sched = ManualScheduler()
    caught = []

    def boom(dt):
        raise ValueError("nope")

    loop = GameLoop(sched, boom, lambda: None, fps=60,
                    max_consecutive_errors=2, on_error=caught.append)
    loop.start()
    sched.tick(5)

    assert len(caught) == 1
    assert isinstance(caught[0], ValueError)
    assert loop.error is not None
    assert sched.pending_count == 0


# ── Retuning the frame rate ─────────────────────────────────────────
#
# A host that seats several games needs this: a menu can idle slowly and hand
# over to something real-time without tearing the loop down and rebuilding it.


def test_target_fps_reports_what_is_being_aimed_for():
    loop = GameLoop(ManualScheduler(), lambda dt: None, lambda: None, fps=30)
    assert round(loop.target_fps) == 30


def test_target_fps_can_be_changed_while_running():
    sched = ManualScheduler()
    loop = GameLoop(sched, lambda dt: None, lambda: None, fps=10)
    loop.start()
    assert round(loop.target_fps) == 10

    loop.target_fps = 60
    assert round(loop.target_fps) == 60
    sched.tick(2)          # still ticking after the change
    loop.stop()


def test_target_fps_is_distinct_from_the_measured_rate():
    # `fps` reports what actually happened; `target_fps` what was asked for.
    loop = GameLoop(ManualScheduler(), lambda dt: None, lambda: None, fps=30)
    assert loop.fps == 0.0            # nothing measured yet
    assert round(loop.target_fps) == 30


def test_the_interval_quantizes_to_whole_milliseconds():
    # 60 fps is 16 ms, which is really 62.5 — target_fps reports the intent and
    # interval_ms reports what the scheduler will actually do.
    loop = GameLoop(ManualScheduler(), lambda dt: None, lambda: None, fps=60)
    assert loop.target_fps == 60
    assert loop.interval_ms == 16


def test_an_absurd_frame_rate_cannot_produce_a_zero_delay():
    loop = GameLoop(ManualScheduler(), lambda dt: None, lambda: None, fps=30)
    loop.target_fps = 100000
    assert loop.interval_ms >= 1
    loop.target_fps = 0               # would divide by zero if unguarded
    assert loop.interval_ms >= 1
