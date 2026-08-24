"""EntityGroup tests — all headless."""
from texastoast.world import Entity, EntityGroup


class Counter:
    """A duck-typed member: has update(dt), is not an Entity."""

    def __init__(self):
        self.updates = 0.0

    def update(self, dt):
        self.updates += dt


def test_update_calls_each_member():
    group = EntityGroup()
    a, b = Counter(), Counter()
    group.add(a)
    group.add(b)
    group.update(0.5)
    assert a.updates == 0.5
    assert b.updates == 0.5


def test_add_returns_the_entity():
    group = EntityGroup()
    e = Entity(x=1)
    assert group.add(e, "player") is e


def test_add_during_update_applies_after_the_pass():
    # Regression shape: appending to the list being iterated could run the
    # new member's update in the same pass (or blow up); the group defers.
    group = EntityGroup()
    late = Counter()

    class Spawner:
        def update(self, dt):
            if late not in group:
                group.add(late)

    group.add(Spawner())
    group.update(1.0)
    assert late in group
    assert late.updates == 0.0     # joined after the pass, not during

    group.update(1.0)
    assert late.updates == 1.0


def test_remove_during_update_does_not_skip_neighbors():
    # The classic bug: removing from a list mid-iteration skips the next
    # element. Every member must still be updated this pass.
    group = EntityGroup()
    members = [Counter() for _ in range(4)]

    class Assassin:
        def update(self, dt):
            group.remove(members[1])

    group.add(Assassin())
    for m in members:
        group.add(m)

    group.update(1.0)
    assert all(m.updates == 1.0 for m in members)   # nobody skipped
    assert members[1] not in group                   # but the removal landed


def test_alive_false_is_culled_after_update():
    group = EntityGroup()

    class Mayfly(Entity):
        def update(self, dt):
            self.alive = False

    fly = group.add(Mayfly())
    assert fly in group
    group.update(1.0)
    assert fly not in group
    assert len(group) == 0


def test_member_without_alive_attribute_is_immortal():
    group = EntityGroup()
    c = group.add(Counter())
    group.update(1.0)
    assert c in group


def test_tags_and_by_tag():
    group = EntityGroup()
    npc1 = group.add(Entity(x=1), "npc")
    npc2 = group.add(Entity(x=2), "npc", "vendor")
    group.add(Entity(x=3), "player")

    assert group.by_tag("npc") == [npc1, npc2]
    assert group.by_tag("vendor") == [npc2]
    assert group.by_tag("ghost") == []


def test_removed_entity_leaves_the_tag_index():
    group = EntityGroup()
    npc = group.add(Entity(), "npc")
    group.remove(npc)
    assert group.by_tag("npc") == []
    # A double remove is not an error.
    group.remove(npc)


def test_select_predicate():
    group = EntityGroup()
    group.add(Entity(x=10))
    far = group.add(Entity(x=100))
    assert group.select(lambda e: e.x > 50) == [far]


def test_sorted_by_y_uses_the_feet_line():
    # A short entity standing lower must draw in front of a tall entity whose
    # top is lower but whose feet are higher — painter's order is by baseline.
    group = EntityGroup()
    tall = group.add(Entity(y=10, height=32))    # feet at 42
    short = group.add(Entity(y=30, height=8))    # feet at 38
    assert group.sorted_by_y() == [short, tall]


def test_len_iter_contains_clear():
    group = EntityGroup()
    e = group.add(Entity(), "npc")
    assert len(group) == 1
    assert list(group) == [e]
    assert e in group

    group.clear()
    assert len(group) == 0
    assert e not in group
    assert group.by_tag("npc") == []
