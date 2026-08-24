"""I2C bus abstraction with smbus2 + graceful fallback.

If smbus2 is not installed (e.g., on macOS or non-RPi systems),
a mock bus is used that returns dummy data. Games can still run
with keyboard input.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from smbus2 import SMBus
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    logger.info("smbus2 not available — I2C hardware disabled")


class I2CBus:
    """Wrapper around smbus2 with error handling and mock fallback.

    ``backend`` accepts any object with the smbus2 surface this class uses
    (``read_byte``, ``read_byte_data``, ``write_byte_data``,
    ``read_i2c_block_data``, ``write_i2c_block_data``, ``close``) — e.g. a
    :class:`~texastoast.i2c.sim.SimBus`. A bus with an injected backend is a
    *real* bus to every caller: ``is_mock`` stays False and reads flow through,
    which is what lets the whole hub/protocol stack run against a simulator.
    """

    def __init__(self, bus_number: int = 1, backend: object | None = None):
        self._bus_number = bus_number
        self._bus: object | None = backend
        if backend is not None:
            self._mock = False
        else:
            self._mock = not HAS_SMBUS
            self._open()

    def _open(self):
        if self._mock:
            logger.warning(f"I2C bus {self._bus_number} running in MOCK mode")
            return
        try:
            self._bus = SMBus(self._bus_number)
            logger.info(f"I2C bus {self._bus_number} opened")
        except FileNotFoundError:
            logger.warning(f"I2C bus {self._bus_number} not found — falling back to mock")
            self._mock = True
        except PermissionError:
            logger.warning(f"I2C bus {self._bus_number} permission denied — falling back to mock")
            self._mock = True
        except OSError as e:
            logger.warning(f"I2C bus {self._bus_number} error: {e} — falling back to mock")
            self._mock = True

    @property
    def is_mock(self) -> bool:
        return self._mock

    @property
    def bus_number(self) -> int:
        return self._bus_number

    def read_byte_data(self, address: int, register: int) -> int | None:
        """Read one byte. Returns ``None`` if the read failed or the bus is mock.

        A failed read must be distinguishable from a device that genuinely
        reported 0x00, otherwise callers cannot tell whether hardware is
        present at all.
        """
        if self._mock:
            return None
        try:
            return self._bus.read_byte_data(address, register)
        except OSError as e:
            logger.debug(f"I2C read error at 0x{address:02x}: {e}")
            return None

    def write_byte_data(self, address: int, register: int, value: int):
        if self._mock:
            return
        try:
            self._bus.write_byte_data(address, register, value)
        except OSError as e:
            logger.debug(f"I2C write error at 0x{address:02x}: {e}")

    def read_i2c_block_data(self, address: int, register: int,
                            length: int) -> list[int] | None:
        """Read a block of bytes. Returns ``None`` if the read failed or the
        bus is mock. See :meth:`read_byte_data` for why."""
        if self._mock:
            return None
        try:
            return self._bus.read_i2c_block_data(address, register, length)
        except OSError as e:
            logger.debug(f"I2C block read error at 0x{address:02x}: {e}")
            return None

    def write_i2c_block_data(self, address: int, register: int, data: list[int]):
        if self._mock:
            return
        try:
            self._bus.write_i2c_block_data(address, register, data)
        except OSError as e:
            logger.debug(f"I2C block write error at 0x{address:02x}: {e}")

    def probe(self, address: int) -> bool:
        """Whether a device answers at ``address``. One read, no sweep."""
        if self._mock:
            return False
        try:
            self._bus.read_byte(address)
            return True
        except OSError:
            return False

    def scan(self, start: int = 0x03, end: int = 0x77) -> list[int]:
        """Scan I2C bus for devices. Returns list of responding addresses.

        This probes every address in the range — 117 blocking reads by
        default — so it belongs in diagnostics, not on a game's startup path.
        Use :meth:`probe` for known candidate addresses instead.
        """
        if self._mock:
            return []
        found = []
        for addr in range(start, end + 1):
            if self.probe(addr):
                found.append(addr)
        return found

    def close(self):
        if self._bus is not None:
            try:
                self._bus.close()
            except Exception:
                pass
            self._bus = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
