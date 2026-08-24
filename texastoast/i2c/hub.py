"""I2C hub abstraction — reads controller state from I2C slave devices."""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass

from texastoast.i2c.bus import I2CBus
from texastoast.i2c.protocol import (
    CONTROLLER_SIZE,
    DEFAULT_HUB_ADDRESSES,
    ControllerState,
)

logger = logging.getLogger(__name__)

# Rolling window for poll-duration stats: ~4 seconds at the default cadence.
_STATS_WINDOW = 120


@dataclass(frozen=True)
class HubStats:
    """Snapshot of a hub's polling health.

    Frozen so a reader on another thread gets one coherent picture; a fresh
    instance is built on every :attr:`MagmaHub.stats` access.
    """

    poll_count: int = 0
    error_count: int = 0
    last_poll_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    avg_duration: float = 0.0

    @property
    def jitter(self) -> float:
        """Spread of poll durations over the rolling window, in seconds."""
        return self.max_duration - self.min_duration


class MagmaHub:
    """Represents one Magma Hub (Pico I2C slave) with N controllers."""

    def __init__(
        self,
        address: int,
        bus: I2CBus,
        num_controllers: int = 1,
        poll_interval: float = 0.016,
    ):
        self._address = address
        self._bus = bus
        self._num_controllers = num_controllers
        self._poll_interval = poll_interval
        self._states: list[ControllerState] = [
            ControllerState() for _ in range(num_controllers)
        ]
        self._last_poll = 0.0
        self._connected = False
        self._poll_count = 0
        self._error_count = 0
        self._durations: deque[float] = deque(maxlen=_STATS_WINDOW)
        self._last_duration = 0.0

    @property
    def address(self) -> int:
        return self._address

    @property
    def num_controllers(self) -> int:
        return self._num_controllers

    @property
    def connected(self) -> bool:
        """Whether the last :meth:`poll` actually read a controller.

        ``False`` until a successful poll, and ``False`` again as soon as reads
        start failing or the bus is mock.
        """
        return self._connected

    @property
    def stats(self) -> HubStats:
        """Polling health counters, as an immutable snapshot."""
        durations = tuple(self._durations)
        return HubStats(
            poll_count=self._poll_count,
            error_count=self._error_count,
            last_poll_duration=self._last_duration,
            min_duration=min(durations) if durations else 0.0,
            max_duration=max(durations) if durations else 0.0,
            avg_duration=sum(durations) / len(durations) if durations else 0.0,
        )

    def poll(self) -> list[ControllerState]:
        """Read all controller states from the hub.
        Uses the protocol: write [start_addr, num_bytes], then read.

        The returned list is a fresh snapshot; treat it as read-only. A new
        list is built and swapped in with a single assignment so that a reader
        on another thread (see :class:`~texastoast.i2c.poller.HubPoller`) can
        never observe a half-updated poll.
        """
        now = time.monotonic()
        if now - self._last_poll < self._poll_interval:
            return self._states

        self._last_poll = now
        self._poll_count += 1

        any_ok = False
        old_states = self._states
        new_states: list[ControllerState] = []
        for i in range(self._num_controllers):
            state = old_states[i] if i < len(old_states) else ControllerState()
            try:
                start_addr = i * CONTROLLER_SIZE
                data = self._read_block(start_addr, CONTROLLER_SIZE)
                if data is not None and len(data) >= CONTROLLER_SIZE:
                    state = ControllerState(buttons=data[0], joystick=data[1])
                    any_ok = True
                else:
                    self._error_count += 1
            except Exception as e:
                self._error_count += 1
                logger.debug(f"Hub 0x{self._address:02x} ctrl {i} read error: {e}")
            new_states.append(state)

        duration = time.monotonic() - now
        self._last_duration = duration
        self._durations.append(duration)

        # Connected if *any* controller answered. Assigned once, after the loop:
        # assigning per-controller let the last one overwrite the others.
        self._connected = any_ok
        self._states = new_states
        return new_states

    def get_controller(self, index: int) -> ControllerState:
        states = self._states
        if 0 <= index < len(states):
            return states[index]
        return ControllerState()

    def _read_block(self, start_addr: int, num_bytes: int) -> list[int] | None:
        """Read a block from the hub using the magma protocol.

        Returns ``None`` when the read fails or the bus is mock, so that
        :meth:`poll` can tell "no hardware" apart from "all buttons released".
        """
        if self._bus.is_mock:
            return None

        try:
            # Protocol: write [start_addr, num_bytes], then read
            self._bus.write_i2c_block_data(
                self._address, start_addr, [num_bytes]
            )
            time.sleep(0.001)
            return self._bus.read_i2c_block_data(
                self._address, start_addr, num_bytes
            )
        except Exception as e:
            logger.debug(f"I2C read block error: {e}")
            return None

    @classmethod
    def scan_buses(cls, bus_numbers: list[int] = None,
                   addresses: list[int] = None,
                   num_controllers: int = 1,
                   buses: list[I2CBus] = None) -> list[MagmaHub]:
        """Probe candidate addresses and create a MagmaHub for each that answers.

        Only the candidate ``addresses`` are probed (four reads by default),
        not the whole 0x03–0x77 range — a full sweep is 117 blocking reads and
        has no place on a game's startup path. Pass pre-built ``buses`` (e.g.
        simulator-backed ones) to scan those instead of opening by number.
        """
        if addresses is None:
            addresses = DEFAULT_HUB_ADDRESSES
        if buses is None:
            if bus_numbers is None:
                bus_numbers = [1]
            buses = [I2CBus(n) for n in bus_numbers]

        hubs = []
        for bus in buses:
            if bus.is_mock:
                logger.info(f"Bus {bus.bus_number} is mock — skipping scan")
                bus.close()
                continue

            claimed = False
            for addr in addresses:
                if bus.probe(addr):
                    hub = cls(addr, bus, num_controllers=num_controllers)
                    hubs.append(hub)
                    claimed = True
                    logger.info(f"Found Magma Hub at 0x{addr:02x}")

            # Only the hubs we return keep the bus alive; otherwise close it.
            if not claimed:
                bus.close()

        return hubs
