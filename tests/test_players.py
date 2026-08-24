"""PlayerManager tests — hotplug driven entirely through SimBus, headless."""
from texastoast.i2c.protocol import BTN_A, BTN_START, BTN_UP
from texastoast.i2c.sim import simulated_hub
from texastoast.input.abstract import InputState
from texastoast.input.players import Player, PlayerManager


class FakeSource:
    """A scriptable InputSource without a `connected` attribute (keyboard-like)."""

    def __init__(self):
        self.state = InputState()

    def poll(self):
        return self.state

    def is_pressed(self, button):
        return getattr(self.state, button, False)


def test_fresh_press_joins_first_free_seat():
    manager = PlayerManager()
    source = FakeSource()
    manager.add_source(source)

    manager.update()                       # idle — nothing joins
    assert manager.joined_players == ()

    source.state = InputState(a=True)
    manager.update()
    assert len(manager.joined_players) == 1
    assert manager.player(0).source is source


def test_held_button_does_not_join_per_frame():
    # Edge-triggered: the press that joins must be fresh. Holding A through
    # the join screen claims one seat, not one per frame.
    manager = PlayerManager()
    a, b = FakeSource(), FakeSource()
    manager.add_source(a)
    manager.add_source(b)

    a.state = InputState(a=True)
    manager.update()
    manager.update()   # still held
    manager.update()
    assert len(manager.joined_players) == 1


def test_join_and_leave_callbacks():
    events = []
    manager = PlayerManager(on_join=lambda p: events.append(("join", p.index)),
                            on_leave=lambda p: events.append(("leave", p.index)))
    source = FakeSource()
    manager.add_source(source)
    source.state = InputState(start=True)
    manager.update()
    assert events == [("join", 0)]

    manager.release(manager.player(0))
    assert events == [("join", 0), ("leave", 0)]


def test_max_players_respected():
    manager = PlayerManager(max_players=1)
    a, b = FakeSource(), FakeSource()
    manager.add_source(a)
    manager.add_source(b)
    a.state = InputState(a=True)
    b.state = InputState(a=True)
    manager.update()
    assert len(manager.joined_players) == 1


def test_join_buttons_configurable():
    manager = PlayerManager(join_buttons=("up",))
    source = FakeSource()
    manager.add_source(source)

    source.state = InputState(a=True)      # A is not a join button here
    manager.update()
    assert manager.joined_players == ()

    source.state = InputState(up=True, a=True)
    manager.update()
    assert len(manager.joined_players) == 1


def test_player_duck_types_input_source():
    manager = PlayerManager()
    source = FakeSource()
    manager.add_source(source)
    source.state = InputState(a=True)
    manager.update()

    player = manager.player(0)
    source.state = InputState(right=True)
    assert player.poll().right is True
    assert player.is_pressed("right") is True
    assert isinstance(player, Player)


def test_release_frees_the_seat_for_rejoin():
    manager = PlayerManager()
    source = FakeSource()
    manager.add_source(source)
    source.state = InputState(a=True)
    manager.update()
    manager.release(manager.player(0))
    assert not manager.player(0).joined

    # The released source is claimable again — but needs a fresh press.
    source.state = InputState(a=True)
    manager.update()   # held from before release? prev was reset to idle → fresh
    assert manager.player(0).joined


# ── hotplug via the simulator ───────────────────────────────────────

def _joined_hub_manager(events=None):
    """A manager with one hub-backed seat already joined."""
    hub, sim = simulated_hub()
    manager = PlayerManager(
        on_join=(lambda p: events.append(("join", p.index))) if events is not None else None,
        on_leave=(lambda p: events.append(("leave", p.index))) if events is not None else None,
    )
    manager.add_hub(hub)
    sim.press(BTN_A)
    hub.poll()
    manager.update()          # fresh A → seat 0 joins
    sim.release(BTN_A)
    hub.poll()
    return manager, hub, sim


def test_add_hub_registers_one_source_per_controller():
    hub, sim = simulated_hub(num_controllers=2)
    manager = PlayerManager()
    manager.add_hub(hub)
    sim.press(BTN_A, index=0)
    sim.press(BTN_START, index=1)
    hub.poll()
    manager.update()
    assert len(manager.joined_players) == 2


def test_disconnect_marks_inactive_and_fires_on_leave():
    events = []
    manager, hub, sim = _joined_hub_manager(events)
    assert events == [("join", 0)]

    sim.disconnect_hub(0x08)
    hub.poll()                # reads fail → hub.connected False
    manager.update()
    assert events == [("join", 0), ("leave", 0)]
    assert manager.player(0).joined      # the seat keeps its source
    assert not manager.player(0).active


def test_inactive_player_polls_idle_not_stuck():
    # THE regression this exists for: the buttons held at the moment of
    # disconnect must not stay pressed forever.
    manager, hub, sim = _joined_hub_manager()
    sim.press(BTN_UP)
    hub.poll()
    assert manager.player(0).poll().up is True

    sim.disconnect_hub(0x08)
    hub.poll()
    manager.update()
    state = manager.player(0).poll()
    assert state.up is False
    assert state == InputState()


def test_reconnect_reclaims_same_slot_and_refires_on_join():
    events = []
    manager, hub, sim = _joined_hub_manager(events)
    sim.disconnect_hub(0x08)
    hub.poll()
    manager.update()

    sim.reconnect_hub(0x08)
    hub.poll()
    manager.update()
    assert events == [("join", 0), ("leave", 0), ("join", 0)]
    assert manager.player(0).active


def test_reconnect_does_not_steal_another_seat():
    hub, sim = simulated_hub()
    manager = PlayerManager()
    keyboard = FakeSource()
    manager.add_hub(hub)
    manager.add_source(keyboard)

    # Hub joins seat 0.
    sim.press(BTN_A)
    hub.poll()
    manager.update()
    sim.release(BTN_A)
    hub.poll()

    # Hub drops; keyboard joins seat 1 meanwhile.
    sim.disconnect_hub(0x08)
    hub.poll()
    manager.update()
    keyboard.state = InputState(a=True)
    manager.update()
    assert manager.player(1).source is keyboard

    # Hub returns: back to seat 0, keyboard untouched.
    sim.reconnect_hub(0x08)
    hub.poll()
    manager.update()
    assert manager.player(0).active
    assert manager.player(1).source is keyboard


def test_keyboard_source_never_leaves():
    # No `connected` attribute → treated as always connected.
    events = []
    manager = PlayerManager(on_leave=lambda p: events.append("leave"))
    source = FakeSource()
    manager.add_source(source)
    source.state = InputState(a=True)
    manager.update()
    for _ in range(5):
        manager.update()
    assert events == []
    assert manager.player(0).active


def test_disconnected_source_cannot_join():
    hub, sim = simulated_hub()
    manager = PlayerManager()
    manager.add_hub(hub)
    sim.disconnect_hub(0x08)
    hub.poll()
    manager.update()
    assert manager.joined_players == ()
