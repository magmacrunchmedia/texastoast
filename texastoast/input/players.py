"""Multi-controller player management — seats, join-by-press, hotplug.

Wiring 2–4 controllers by hand means tracking which hub index belongs to
which player, noticing when a controller vanishes mid-game, and making sure
its buttons don't stay stuck down. :class:`PlayerManager` owns all of that:

    manager = PlayerManager(max_players=2, on_join=show_banner)
    manager.add_source(keyboard)          # the keyboard is a claimable seat too
    manager.add_hub(poller)               # one seat candidate per controller

    def update(dt):
        manager.update()                  # join scan + hotplug watch
        for player in manager.joined_players:
            state = player.poll()         # a Player IS an InputSource
            ...

Frame-driven like the UI widgets: call :meth:`PlayerManager.update` once per
frame. Joining is edge-triggered — a *fresh* press of a join button claims the
first free seat; holding the button through the join screen claims one seat,
not one per frame.

Hotplug follows the house rules. Sources expose ``connected`` by duck-typing
(``MagmaHubInput`` forwards its hub's; ``KeyboardInput`` has none and so never
leaves). When a controller vanishes its seat goes **inactive and idle** — not
stuck holding whatever was pressed at the moment of disconnect. When it comes
back it **reclaims the same seat** and ``on_join`` fires again: a bounced hub
cable is the same physical controller, and reshuffling P1/P2 mid-game is
exactly the failure a living-room console must not have.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from texastoast.input.abstract import InputState

logger = logging.getLogger(__name__)

_IDLE = InputState()


class Player:
    """One seat. Duck-types InputSource (``poll``/``is_pressed``), so game
    code written against a KeyboardInput takes a Player unchanged."""

    def __init__(self, index: int):
        self.index = index
        self._source = None
        self._active = False

    @property
    def source(self):
        return self._source

    @property
    def joined(self) -> bool:
        """A source has claimed this seat (it may be temporarily inactive)."""
        return self._source is not None

    @property
    def active(self) -> bool:
        """Joined and the source is currently connected."""
        return self._active

    def poll(self) -> InputState:
        """The seat's input — idle unless active. An inactive seat must never
        report the buttons that were held at the moment of disconnect."""
        if self._active and self._source is not None:
            return self._source.poll()
        return replace(_IDLE)

    def is_pressed(self, button: str) -> bool:
        if self._active and self._source is not None:
            return self._source.is_pressed(button)
        return False


class PlayerManager:
    """Assigns input sources to player seats and watches their health.

    ``on_join(player)`` fires when a seat is claimed — and again when a
    disconnected controller comes back (same seat; there is deliberately no
    separate ``on_rejoin``). ``on_leave(player)`` fires when a seat's source
    disconnects or is :meth:`release`\\ d. Both are called synchronously from
    :meth:`update`, on the game thread.
    """

    def __init__(
        self,
        max_players: int = 4,
        join_buttons: tuple[str, ...] = ("a", "start"),
        on_join: Callable[[Player], None] | None = None,
        on_leave: Callable[[Player], None] | None = None,
    ):
        self._players = tuple(Player(i) for i in range(max_players))
        self._join_buttons = join_buttons
        self._on_join = on_join
        self._on_leave = on_leave
        self._unassigned: list = []
        # Previous frame's state per unassigned source, for edge detection.
        self._prev: dict[int, InputState] = {}

    @property
    def players(self) -> tuple[Player, ...]:
        """Every seat, joined or not, in index order."""
        return self._players

    @property
    def joined_players(self) -> tuple[Player, ...]:
        return tuple(p for p in self._players if p.joined)

    def player(self, index: int) -> Player:
        return self._players[index]

    def add_source(self, source):
        """Offer ``source`` (any InputSource) as claimable by a join press."""
        self._unassigned.append(source)
        self._prev[id(source)] = replace(_IDLE)

    def add_hub(self, hub):
        """Offer every controller on ``hub`` (a MagmaHub or HubPoller — both
        expose ``num_controllers``) as a claimable source."""
        from texastoast.input.magma_hub import MagmaHubInput

        for i in range(hub.num_controllers):
            self.add_source(MagmaHubInput(hub, controller_index=i))

    def release(self, player: Player):
        """Manually un-join a seat ("drop out" in a menu). The source returns
        to the claimable pool."""
        source = player._source
        if source is None:
            return
        was_active = player._active
        player._source = None
        player._active = False
        self._unassigned.append(source)
        self._prev[id(source)] = replace(_IDLE)
        if was_active and self._on_leave:
            self._on_leave(player)

    def update(self):
        """One frame of seat management: watch joined seats' connections,
        then scan unassigned sources for a fresh join press."""
        self._watch_connections()
        self._scan_joins()

    # ── internals ───────────────────────────────────────────────────

    def _watch_connections(self):
        for player in self._players:
            if not player.joined:
                continue
            if not player._active:
                # Nothing else polls an inactive seat's source, and a
                # direct-wired hub only refreshes `connected` when polled —
                # without this, a seat could never notice its controller
                # coming back. With a HubPoller this is a free snapshot read.
                player._source.poll()
            connected = getattr(player._source, "connected", True)
            if player._active and not connected:
                player._active = False
                logger.info(f"Player {player.index}: controller disconnected")
                if self._on_leave:
                    self._on_leave(player)
            elif not player._active and connected:
                # The same seat reclaims its returning controller — a bounced
                # cable must not reshuffle who is P1 and who is P2.
                player._active = True
                logger.info(f"Player {player.index}: controller back")
                if self._on_join:
                    self._on_join(player)

    def _scan_joins(self):
        if not self._unassigned:
            return
        for source in list(self._unassigned):
            if getattr(source, "connected", True) is False:
                continue
            state = source.poll()
            prev = self._prev[id(source)]
            fresh = any(
                getattr(state, b, False) and not getattr(prev, b, False)
                for b in self._join_buttons
            )
            self._prev[id(source)] = state
            if not fresh:
                continue
            seat = next((p for p in self._players if not p.joined), None)
            if seat is None:
                return  # all seats taken; leave the source claimable
            self._unassigned.remove(source)
            self._prev.pop(id(source), None)
            seat._source = source
            seat._active = True
            logger.info(f"Player {seat.index}: joined")
            if self._on_join:
                self._on_join(seat)
