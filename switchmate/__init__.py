"""Library to handle connection with Switchmate"""

import asyncio
import logging

import bleak

CONNECT_LOCK = asyncio.Lock()

ON_KEY = b'\x01'
OFF_KEY = b'\x00'

_LOGGER = logging.getLogger(__name__)


class Switchmate:
    """Representation of a Switchmate."""

    def __init__(self, mac, flip_on_off=False) -> None:
        self._mac = mac
        self.state = False
        self._device = None
        self.available = False
        self._flip_on_off = flip_on_off
        self._handle = None

    async def _connect(self) -> bool:
        # Disconnect before reconnecting
        if self._device is not None:
            await self._disconnect()
        _LOGGER.debug("Connecting")
        self._device = bleak.BleakClient(self._mac)
        try:
            async with CONNECT_LOCK:
                await self._device.connect()
                if self._handle is None:
                    # Determine state/control handle based on Switchmate model
                    self._handle = (45 if await self._device.read_gatt_char(19)
                                    == b'Original' else 47)
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            _LOGGER.error("Failed to connect to switchmate",
                          exc_info=logging.DEBUG >= _LOGGER.root.level)
            self.available = False
            return False
        self.available = True
        return True

    async def _disconnect(self) -> None:
        _LOGGER.debug("Disconnecting")
        try:
            await self._device.disconnect()
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            pass

    async def _sendpacket(self, key, retry=2) -> bool:
        _LOGGER.debug("Sending key %s", key)
        try:
            async with CONNECT_LOCK:
                await self._device.write_gatt_char(self._handle, key, True)
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry < 1 or not await self._connect():
                _LOGGER.error("Cannot connect to switchmate.",
                              exc_info=logging.DEBUG >= _LOGGER.root.level)
                self.available = False
                return False
            return await self._sendpacket(key, retry-1)
        self.available = True
        return True

    async def update(self, retry=2) -> None:
        """Synchronize state with switch."""
        _LOGGER.debug("Updating device state.")
        key = ON_KEY if not self._flip_on_off else OFF_KEY
        try:
            async with CONNECT_LOCK:
                self.state = (
                    await self._device.read_gatt_char(self._handle) == key)
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry < 1 or not await self._connect():
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
