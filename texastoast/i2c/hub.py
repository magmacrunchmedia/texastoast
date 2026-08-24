"""MagmaHub — abstracts one or more controllers on an I2C slave Pico."""

from __future__ import annotations

import logging
import time
from typing import Optional

from texastoast.i2c.bus import I2CBus
from texastoast.i2c.protocol import (
    CONTROLLER_SIZE,
    BUTTONS_ADDR,
    JOYSTICK_ADDR,
    ControllerState,
    DEFAULT_HUB_ADDRESSES,
)

logger = logging.getLogger(__name__)


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

    @property
    def address(self) -> int:
        return self._address

    @property
    def num_controllers(self) -> int:
        return self._num_controllers

    @property
    def connected(self) -> bool:
        return self._connected

    def poll(self) -> list[ControllerState]:
        """Read all controller states from the hub.
        Uses the protocol: write [start_addr, num_bytes], then read."""
        now = time.monotonic()
        if now - self._last_poll < self._poll_interval:
            return self._states

        self._last_poll = now

        for i in range(self._num_controllers):
            try:
                start_addr = i * CONTROLLER_SIZE
                data = self._read_block(start_addr, CONTROLLER_SIZE)
                if data and len(data) >= CONTROLLER_SIZE:
                    self._states[i] = ControllerState(
                        buttons=data[0],
                        joystick=data[1],
                    )
                    self._connected = True
            except Exception as e:
                logger.debug(f"Hub 0x{self._address:02x} ctrl {i} read error: {e}")
                self._connected = False

        return self._states

    def get_controller(self, index: int) -> ControllerState:
        if 0 <= index < self._num_controllers:
            return self._states[index]
        return ControllerState()

    def _read_block(self, start_addr: int, num_bytes: int) -> list[int]:
        """Read block from hub using the magma protocol."""
        if self._bus.is_mock:
            return [0x00] * num_bytes

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
            return [0x00] * num_bytes

    @classmethod
    def scan_buses(cls, bus_numbers: list[int] = None,
                   addresses: list[int] = None,
                   num_controllers: int = 1) -> list[MagmaHub]:
        """Scan I2C buses and create MagmaHub instances for found devices."""
        if bus_numbers is None:
            bus_numbers = [1]
        if addresses is None:
            addresses = DEFAULT_HUB_ADDRESSES

        hubs = []
        for bus_num in bus_numbers:
            bus = I2CBus(bus_num)
            if bus.is_mock:
                logger.info(f"Bus {bus_num} is mock — skipping scan")
                bus.close()
                continue

            found = bus.scan()
            logger.info(f"Bus {bus_num} scan: {[f'0x{a:02x}' for a in found]}")

            for addr in found:
                if addr in addresses:
                    hub = cls(addr, bus, num_controllers=num_controllers)
                    hubs.append(hub)
                    logger.info(f"Found Magma Hub at 0x{addr:02x}")

        return hubs
