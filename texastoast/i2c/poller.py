"""Background polling for Magma Hubs.

I2C reads block the calling thread — a loose wire can turn one ``poll()``
into a visible frame hitch. :class:`HubPoller` moves the bus traffic onto a
daemon thread and hands the game an always-fresh snapshot instead.

The poller duck-types :class:`~texastoast.i2c.hub.MagmaHub`'s read surface
(``poll``, ``get_controller``, ``connected``, ``stats``, ``address``,
``num_controllers``), so ``MagmaHubInput`` and the rest of the input chain
work unchanged — a poller is just a hub whose ``poll()`` never touches the
bus. Use one poller per hub *or* poll the hub directly, never both: two
callers would fight the hub's own poll-interval throttle.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable

from texastoast.i2c.hub import HubStats, MagmaHub
from texastoast.i2c.protocol import ControllerState

logger = logging.getLogger(__name__)


class HubPoller:
    """Polls a :class:`MagmaHub` on a daemon thread.

    ``poll()`` returns the latest snapshot without any I/O. The handoff is a
    single assignment of an immutable tuple — atomic under the GIL — so the
    hot path needs no lock on either side.

    Wire teardown into the game's lifecycle::

        poller = HubPoller(hub).start()
        game.on_close(poller.stop)
    """

    def __init__(self, hub: MagmaHub, poll_interval: float = 0.008):
        # Deliberately faster than a 30 fps frame: the snapshot the game reads
        # is then never more than ~half a frame stale.
        self._hub = hub
        self._poll_interval = poll_interval
        self._snapshot: tuple[ControllerState, ...] = tuple(
            ControllerState() for _ in range(hub.num_controllers)
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> HubPoller:
        """Start the polling thread. Returns self for one-line wiring."""
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"HubPoller-0x{self._hub.address:02x}",
            daemon=True,
        )
        self._thread.start()
        return self

    def stop(self, timeout: float = 1.0):
        """Stop and join the polling thread. Safe to call more than once."""
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout)
        self._thread = None

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def _run(self):
        while not self._stop_event.is_set():
            try:
                states = self._hub.poll()
                self._snapshot = tuple(states)
            except Exception:
                # The hub already downgrades bus errors to logs; anything that
                # reaches here is a bug, but the poller must not die silently
                # and leave the game reading a frozen snapshot.
                logger.exception("HubPoller: unexpected error, continuing")
            self._stop_event.wait(self._poll_interval)

    # ── MagmaHub-compatible read surface ────────────────────────────

    def poll(self) -> list[ControllerState]:
        """The latest snapshot. Never blocks, never touches the bus."""
        return list(self._snapshot)

    def get_controller(self, index: int) -> ControllerState:
        snapshot = self._snapshot
        if 0 <= index < len(snapshot):
            return snapshot[index]
        return ControllerState()

    @property
    def connected(self) -> bool:
        return self._hub.connected

    @property
    def stats(self) -> HubStats:
        return self._hub.stats

    @property
    def address(self) -> int:
        return self._hub.address

    @property
    def num_controllers(self) -> int:
        return self._hub.num_controllers


def scan_buses_async(
    callback: Callable[[list[MagmaHub]], None],
    bus_numbers: list[int] | None = None,
    addresses: list[int] | None = None,
    num_controllers: int = 1,
) -> threading.Thread:
    """Run :meth:`MagmaHub.scan_buses` on a daemon thread.

    ``callback(hubs)`` is invoked *from that thread* — marshal back to
    tkinter with ``root.after(0, ...)`` before touching any widget.
    """

    def _scan():
        started = time.monotonic()
        hubs = MagmaHub.scan_buses(
            bus_numbers=bus_numbers,
            addresses=addresses,
            num_controllers=num_controllers,
        )
        logger.info(
            f"Async scan finished in {time.monotonic() - started:.3f}s: "
            f"{len(hubs)} hub(s)"
        )
        callback(hubs)

    thread = threading.Thread(target=_scan, name="scan_buses_async", daemon=True)
    thread.start()
    return thread
