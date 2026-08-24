"""EntityGroup — holds entities and drives their update(dt).

Before 0.5.0 nothing iterated entities: every game hand-rolled its own list
and its own update loop. The group is that loop, plus safe mid-iteration
add/remove and tag queries. Rendering stays yours — iterate
:meth:`EntityGroup.sorted_by_y` and draw with the renderer; the group never
draws anything.

Membership is duck-typed: anything with ``update(dt)`` qualifies — an Entity,
a particle, a timer object. Tags are therefore indexed *in the group*, not on
the members, so objects that never heard of texastoast fit without growing
attributes.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator


class EntityGroup:
    """A collection of updatable objects.

    Two removal paths, each earning its place:

    * ``entity.alive = False`` — an entity dies inside its own ``update()``
      without holding a reference back to its group; the group culls it after
      the pass. Objects without an ``alive`` attribute are immortal by default.
    * :meth:`remove` — external despawn (a scene removing an NPC).

    Both are deferred: mutating the member list while ``update()`` iterates it
    is the classic first bug of every entity system (the removed entity's
    neighbor gets skipped), so adds and removes queue up and apply after the
    pass.
    """

    def __init__(self):
        self._entities: list = []
        self._tags: dict[str, list] = {}
        self._entity_tags: dict[int, tuple[str, ...]] = {}
        self._pending_add: list[tuple[object, tuple[str, ...]]] = []
        self._pending_remove: list = []
        self._updating = False

    def add(self, entity, *tags: str):
        """Add ``entity`` (anything with ``update(dt)``), optionally tagged.

        Returns the entity, for one-line wiring::

            player = group.add(Entity(x=60, y=60), "player")
        """
        if self._updating:
            self._pending_add.append((entity, tags))
        else:
            self._add_now(entity, tags)
        return entity

    def remove(self, entity):
        """Remove ``entity``. Safe to call mid-update; applied after the pass."""
        if self._updating:
            self._pending_remove.append(entity)
        else:
            self._remove_now(entity)

    def update(self, dt: float):
        """Call ``update(dt)`` on every member, then apply deferred changes.

        Members whose ``alive`` attribute is False after the pass are culled.
        """
        self._updating = True
        try:
            for entity in list(self._entities):
                entity.update(dt)
        finally:
            self._updating = False

        for entity in self._entities:
            if getattr(entity, "alive", True) is False:
                self._pending_remove.append(entity)

        for entity, tags in self._pending_add:
            self._add_now(entity, tags)
        self._pending_add.clear()

        for entity in self._pending_remove:
            self._remove_now(entity)
        self._pending_remove.clear()

    def by_tag(self, tag: str) -> list:
        """The members added under ``tag``, in insertion order."""
        return list(self._tags.get(tag, ()))

    def select(self, predicate: Callable[[object], bool]) -> list:
        """The members for which ``predicate(entity)`` is true."""
        return [e for e in self._entities if predicate(e)]

    def sorted_by_y(self) -> list:
        """Members sorted by their feet line (``y + height``), for painter's-
        algorithm rendering — a top-down sprite draws in front of what its
        baseline is below, not what its top edge is below. Members without
        ``y``/``height`` sort first."""
        return sorted(
            self._entities,
            key=lambda e: getattr(e, "y", 0.0) + getattr(e, "height", 0.0),
        )

    def clear(self):
        self._entities.clear()
        self._tags.clear()
        self._entity_tags.clear()
        self._pending_add.clear()
        self._pending_remove.clear()

    def __iter__(self) -> Iterator:
        return iter(self._entities)

    def __len__(self) -> int:
        return len(self._entities)

    def __contains__(self, entity) -> bool:
        return any(e is entity for e in self._entities)

    # ── internals ───────────────────────────────────────────────────

    def _add_now(self, entity, tags: tuple[str, ...]):
        self._entities.append(entity)
        self._entity_tags[id(entity)] = tags
        for tag in tags:
            self._tags.setdefault(tag, []).append(entity)

    def _remove_now(self, entity):
        try:
            self._entities.remove(entity)
        except ValueError:
            return  # already gone — a double remove is not an error
        for tag in self._entity_tags.pop(id(entity), ()):
            bucket = self._tags.get(tag)
            if bucket is not None:
                try:
                    bucket.remove(entity)
                except ValueError:
                    pass
