"""Scenes — modality as a stack instead of a pile of flags.

Every texastoast game before 0.5.0 hand-rolled its modal state: a ``paused``
global, a ``showing_dialogue`` global, an update() that early-returned while
either was set, and a keypress handler that dispatched down an if-chain. The
scene stack subsumes all of it: **pushing a scene freezes the scenes below by
construction**, so the flags simply stop existing.

There is no base class to subclass. A scene is anything with ``update(dt)``
and ``render()`` — a plain class, a ``SimpleNamespace``, whatever. Everything
else is optional and detected by presence:

* ``on_enter()`` / ``on_exit()`` — pushed onto / removed from the stack
* ``on_pause()`` / ``on_resume()`` — covered by / re-exposed from under a push
* ``handle_key(event)`` — receives key events via :meth:`SceneStack.dispatch_key`
* ``update_below = True`` — the scene under this one keeps updating
* ``render_below = True`` — the scene under this one keeps rendering
  (a pause menu over the visible, frozen world)

The stack is a system you wire, not a framework that owns you::

    stack = SceneStack()
    stack.push(WorldScene())
    game.set_update(stack.update)
    game.set_render(stack.render)
    game.bind_key("<Key>", stack.dispatch_key)

This module imports nothing, knows nothing about Game or tkinter, and is
fully usable headless.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Scene(Protocol):
    """The structural contract: ``update(dt)`` and ``render()`` are required;
    the lifecycle hooks, ``handle_key`` and the ``*_below`` flags documented
    in the module docstring are optional."""

    def update(self, dt: float) -> None: ...

    def render(self) -> None: ...


class SceneStack:
    """A stack of scenes. The top scene runs; scenes below are frozen unless
    the scene above them opts them in with ``update_below``/``render_below``.

    All stack operations are **deferred**: they queue and apply at the start
    of the next :meth:`update`. One rule, two consequences worth knowing —
    a scene may push/pop (even pop itself) mid-update without corrupting the
    frame, and an op issued from a key event (which tkinter delivers between
    frames) lands before the next frame renders, so pressing Escape shows the
    pause menu the same frame.
    """

    def __init__(self):
        self._scenes: list = []
        self._pending: list[tuple[str, object]] = []

    # ── operations (deferred) ───────────────────────────────────────

    def push(self, scene):
        """Put ``scene`` on top. The old top gets ``on_pause``, the new scene
        ``on_enter``."""
        self._pending.append(("push", scene))

    def pop(self):
        """Remove the top scene (``on_exit``); the exposed scene gets
        ``on_resume``. A pop on an empty stack is ignored."""
        self._pending.append(("pop", None))

    def replace(self, scene):
        """Swap the top scene for ``scene``: old top ``on_exit``, new scene
        ``on_enter``. No pause/resume — the scene below never became top."""
        self._pending.append(("replace", scene))

    def clear(self):
        """Remove every scene, firing ``on_exit`` top-down."""
        self._pending.append(("clear", None))

    # ── frame surface (what the game wires) ─────────────────────────

    def update(self, dt: float):
        """Apply pending operations, then update the active slice bottom-to-top.

        The slice is the top scene plus, while each scene sets
        ``update_below``, the scene beneath it. Bottom-to-top so a world that
        updates under an overlay has finished its frame before the overlay
        reads it.
        """
        self._apply_pending()
        for scene in self._slice("update_below"):
            scene.update(dt)

    def render(self):
        """Render the visible slice bottom-to-top (painter's order)."""
        for scene in self._slice("render_below"):
            scene.render()

    def dispatch_key(self, event) -> bool:
        """Forward a key event to the top scene's ``handle_key``, if it has
        one. Top scene only — input modality mirrors update modality.

        The event object is opaque to the stack (headless tests pass any
        object with a ``keysym``). Returns True if a handler saw the event.

        Wire it yourself: ``game.bind_key("<Key>", stack.dispatch_key)`` —
        or ignore this method entirely and keep your own global handler.
        """
        top = self.top
        if top is None:
            return False
        handler = getattr(top, "handle_key", None)
        if handler is None:
            return False
        return bool(handler(event))

    # ── introspection ───────────────────────────────────────────────

    @property
    def top(self):
        """The current top scene, or None. Pending operations are not yet
        reflected — they apply at the next :meth:`update`."""
        return self._scenes[-1] if self._scenes else None

    @property
    def scenes(self) -> tuple:
        """Bottom-to-top snapshot of the stack."""
        return tuple(self._scenes)

    def __len__(self) -> int:
        return len(self._scenes)

    def __bool__(self) -> bool:
        return bool(self._scenes)

    def __contains__(self, scene) -> bool:
        return any(s is scene for s in self._scenes)

    # ── internals ───────────────────────────────────────────────────

    def _slice(self, flag: str) -> list:
        """The active scenes for ``flag``, bottom-to-top: walk down from the
        top while each scene opts the one below it in."""
        active = []
        for i in range(len(self._scenes) - 1, -1, -1):
            scene = self._scenes[i]
            active.append(scene)
            if not getattr(scene, flag, False):
                break
        active.reverse()
        return active

    def _apply_pending(self):
        pending, self._pending = self._pending, []
        for op, scene in pending:
            if op == "push":
                if self._scenes:
                    self._hook(self._scenes[-1], "on_pause")
                self._scenes.append(scene)
                self._hook(scene, "on_enter")
            elif op == "pop":
                if self._scenes:
                    self._hook(self._scenes.pop(), "on_exit")
                    if self._scenes:
                        self._hook(self._scenes[-1], "on_resume")
            elif op == "replace":
                if self._scenes:
                    self._hook(self._scenes.pop(), "on_exit")
                self._scenes.append(scene)
                self._hook(scene, "on_enter")
            elif op == "clear":
                while self._scenes:
                    self._hook(self._scenes.pop(), "on_exit")

    @staticmethod
    def _hook(scene, name: str):
        hook = getattr(scene, name, None)
        if hook is not None:
            hook()
