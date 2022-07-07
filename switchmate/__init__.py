"""Library to handle connection with Switchmate"""

import asyncio
import bleak
import logging

CONNECT_LOCK = asyncio.Lock()

HANDLE = 45  # or 47 for newer "Bright" models

ON_KEY = b'\x01'
OFF_KEY = b'\x00'

_LOGGER = logging.getLogger(__name__)


class Switchmate:
    """Representation of a Switchmate."""

    def __init__(self, mac, flip_on_off=False) -> None:
        self._mac = mac
        self.state = False
        self.available = False
        self._flip_on_off = flip_on_off

    async def _sendpacket(self, key, retry=2) -> bool:
        try:
            _LOGGER.debug("Sending key %s", key)
            async with CONNECT_LOCK:
                async with bleak.BleakClient(self._mac) as client:
                    await client.write_gatt_char(HANDLE, key, True)
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry < 1:
                _LOGGER.error("Cannot connect to switchmate.",
                              exc_info=logging.DEBUG >= _LOGGER.root.level)
                self.available = False
                return False
            return await self._sendpacket(key, retry-1)
        self.available = True
        return True

    async def update(self, retry=2) -> None:
        """Synchronize state with switch."""
        try:
            _LOGGER.debug("Updating device state.")
            key = ON_KEY if not self._flip_on_off else OFF_KEY
            async with CONNECT_LOCK:
                async with bleak.BleakClient(self._mac) as client:
                    self.state = await client.read_gatt_char(HANDLE) == key
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry < 1:
                self.available = False
                _LOGGER.error("Failed to update device state.", exc_info=True)
                return None
            return await self.update(retry-1)
        self.available = True
        return None

    async def turn_on(self) -> bool:
        """Turn the switch on."""
        return await self._sendpacket(ON_KEY if not self._flip_on_off else
                                      OFF_KEY)

    async def turn_off(self) -> bool:
        """Turn the switch off."""
        return await self._sendpacket(OFF_KEY if not self._flip_on_off else
                                      ON_KEY)
