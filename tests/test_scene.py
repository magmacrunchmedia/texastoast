"""SceneStack tests — all headless; scenes are plain objects."""
from types import SimpleNamespace

from texastoast.scene import Scene, SceneStack


class Recorder:
    """A scene that logs everything that happens to it into a shared list."""

    def __init__(self, log, name, update_below=False, render_below=False):
        self.log = log
        self.name = name
        self.update_below = update_below
        self.render_below = render_below

    def update(self, dt):
        self.log.append((self.name, "update", dt))

    def render(self):
        self.log.append((self.name, "render"))

    def on_enter(self):
        self.log.append((self.name, "enter"))

    def on_exit(self):
        self.log.append((self.name, "exit"))

    def on_pause(self):
        self.log.append((self.name, "pause"))

    def on_resume(self):
        self.log.append((self.name, "resume"))

    def handle_key(self, event):
        self.log.append((self.name, "key", event.keysym))
        return True


def make(log=None, **kw):
    log = log if log is not None else []
    return log, Recorder(log, "a", **kw)


# ── lifecycle ───────────────────────────────────────────────────────

def test_push_enters_and_pauses_previous():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.update(0.0)

    stack.push(Recorder(log, "pause"))
    stack.update(0.0)
    hooks = [e for e in log if e[1] in ("enter", "pause", "exit", "resume")]
    assert hooks == [("world", "enter"), ("world", "pause"), ("pause", "enter")]


def test_pop_exits_and_resumes():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.push(Recorder(log, "menu"))
    stack.update(0.0)
    log.clear()

    stack.pop()
    stack.update(0.0)
    assert log[:2] == [("menu", "exit"), ("world", "resume")]


def test_replace_fires_exit_enter_without_pause_resume():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "title"))
    stack.update(0.0)
    log.clear()

    stack.replace(Recorder(log, "world"))
    stack.update(0.0)
    hooks = [e for e in log if e[1] in ("exit", "enter", "pause", "resume")]
    assert hooks == [("title", "exit"), ("world", "enter")]


def test_clear_exits_top_down():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.push(Recorder(log, "menu"))
    stack.update(0.0)
    log.clear()

    stack.clear()
    stack.update(0.0)
    exits = [e for e in log if e[1] == "exit"]
    assert exits == [("menu", "exit"), ("world", "exit")]
    assert len(stack) == 0


def test_missing_hooks_are_fine():
    # A scene can be a bare namespace with only the required surface.
    stack = SceneStack()
    scene = SimpleNamespace(update=lambda dt: None, render=lambda: None)
    stack.push(scene)
    stack.update(1 / 30)
    stack.render()
    stack.pop()
    stack.update(0.0)


def test_pop_on_empty_stack_is_ignored():
    stack = SceneStack()
    stack.pop()
    stack.update(0.0)
    assert len(stack) == 0


# ── modality ────────────────────────────────────────────────────────

def test_only_top_updates_by_default():
    # THE regression this module exists for: pushing a pause scene used to
    # require a `paused` flag checked inside the world's update. Now the
    # world's update simply must not run.
    log = []
    stack = SceneStack()
    world = Recorder(log, "world")
    stack.push(world)
    stack.push(Recorder(log, "pause"))
    stack.update(1 / 30)
    updates = [e for e in log if e[1] == "update"]
    assert updates == [("pause", "update", 1 / 30)]


def test_update_below_chains_bottom_to_top():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.push(Recorder(log, "hud", update_below=True))
    stack.update(1 / 30)
    updates = [e[0] for e in log if e[1] == "update"]
    assert updates == ["world", "hud"]   # bottom first — overlay reads a finished world


def test_render_below_renders_bottom_to_top():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.push(Recorder(log, "pause", render_below=True))
    stack.update(0.0)
    log.clear()

    stack.render()
    renders = [e[0] for e in log if e[1] == "render"]
    assert renders == ["world", "pause"]   # painter's order


def test_flags_do_not_leak_past_a_scene_without_them():
    # dialogue(render_below) over pause(no flags) over world:
    # render shows dialogue + pause, but not world.
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.push(Recorder(log, "pause"))
    stack.push(Recorder(log, "dialogue", render_below=True))
    stack.update(0.0)
    log.clear()

    stack.render()
    renders = [e[0] for e in log if e[1] == "render"]
    assert renders == ["pause", "dialogue"]


# ── deferred operations ─────────────────────────────────────────────

def test_push_during_update_applies_next_frame():
    log = []
    stack = SceneStack()

    class Spawner(Recorder):
        def update(self, dt):
            super().update(dt)
            if len(stack) == 1:
                stack.push(Recorder(log, "overlay"))

    stack.push(Spawner(log, "world"))
    stack.update(1 / 30)
    # The overlay must not have updated in the same frame it was pushed.
    assert [e[0] for e in log if e[1] == "update"] == ["world"]

    stack.update(1 / 30)
    assert [e[0] for e in log if e[1] == "update"] == ["world", "overlay"]


def test_pop_self_during_update_does_not_corrupt_iteration():
    log = []
    stack = SceneStack()

    class SelfPopper(Recorder):
        def update(self, dt):
            super().update(dt)
            stack.pop()

    stack.push(Recorder(log, "world"))
    stack.push(SelfPopper(log, "toast", update_below=True))
    stack.update(1 / 30)   # both update; pop queues
    stack.update(1 / 30)   # pop applies, then world updates alone
    updates = [e[0] for e in log if e[1] == "update"]
    assert updates == ["world", "toast", "world"]
    assert stack.top.name == "world"


def test_op_from_key_handler_lands_before_next_render():
    # tkinter delivers key events between frames; the queued push must apply
    # at the next update — i.e. before that frame renders.
    log = []
    stack = SceneStack()

    class World(Recorder):
        def handle_key(self, event):
            stack.push(Recorder(log, "pause", render_below=True))
            return True

    stack.push(World(log, "world"))
    stack.update(0.0)

    stack.dispatch_key(SimpleNamespace(keysym="Escape"))
    assert stack.top.name == "world"   # not yet — deferred

    stack.update(1 / 30)
    assert stack.top.name == "pause"   # same frame as the next update
    stack.render()
    assert [e[0] for e in log if e[1] == "render"] == ["world", "pause"]


def test_multiple_ops_drain_in_order():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "a"))
    stack.push(Recorder(log, "b"))
    stack.pop()
    stack.update(0.0)
    # push a, push b, pop → a is top.
    assert stack.top.name == "a"


# ── input routing ───────────────────────────────────────────────────

def test_dispatch_key_reaches_top_only():
    log = []
    stack = SceneStack()
    stack.push(Recorder(log, "world"))
    stack.push(Recorder(log, "menu"))
    stack.update(0.0)
    log.clear()

    assert stack.dispatch_key(SimpleNamespace(keysym="z")) is True
    keys = [e for e in log if e[1] == "key"]
    assert keys == [("menu", "key", "z")]


def test_dispatch_key_without_handler_returns_false():
    stack = SceneStack()
    stack.push(SimpleNamespace(update=lambda dt: None, render=lambda: None))
    stack.update(0.0)
    assert stack.dispatch_key(SimpleNamespace(keysym="z")) is False


def test_dispatch_key_on_empty_stack():
    assert SceneStack().dispatch_key(SimpleNamespace(keysym="z")) is False


# ── introspection ───────────────────────────────────────────────────

def test_top_scenes_len_bool_contains():
    log = []
    stack = SceneStack()
    assert not stack
    world = Recorder(log, "world")
    stack.push(world)
    stack.update(0.0)
    assert stack
    assert stack.top is world
    assert stack.scenes == (world,)
    assert len(stack) == 1
    assert world in stack


def test_recorder_satisfies_scene_protocol():
    assert isinstance(Recorder([], "x"), Scene)
