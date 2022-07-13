"""Library to handle connection with Switchmate"""

import asyncio
import logging

import bleak

CONNECT_LOCK = asyncio.Lock()

ON_KEY = b"\x01"
OFF_KEY = b"\x00"

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
                    # Determine handle based on Switchmate model
                    self._handle = (
                        47
                        if await self._device.read_gatt_char(21) == b"Bright"
                        else 45
                    )
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            _LOGGER.error(
                "Failed to connect to Switchmate",
                exc_info=logging.DEBUG >= _LOGGER.root.level,
            )
            return False
        return True

    async def _disconnect(self) -> bool:
        _LOGGER.debug("Disconnecting")
        try:
            async with CONNECT_LOCK:
                await self._device.disconnect()
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            _LOGGER.error(
                "Failed to disconnect from Switchmate",
                exc_info=logging.DEBUG >= _LOGGER.root.level,
            )
            return False
        return True

    async def _communicate(self, key=None, retry=True) -> bool:
        try:
            if (
                self._device is None or not self._device.is_connected
            ) and not await self._connect():
                raise bleak.BleakError("No connection to Switchmate")
            async with CONNECT_LOCK:
                if key:
                    _LOGGER.debug("Sending key %s", key)
                    await self._device.write_gatt_char(self._handle, key, True)
                else:
                    _LOGGER.debug("Updating Switchmate state")
                    self.state = (
                        await self._device.read_gatt_char(self._handle)
                        == ON_KEY
                        if not self._flip_on_off
                        else OFF_KEY
                    )
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry:
                return await self._communicate(key, False)
            _LOGGER.error(
                "Cannot communicate with Switchmate",
                exc_info=logging.DEBUG >= _LOGGER.root.level,
            )
            self.available = False
            return False
        self.available = True
        return True

    async def update(self) -> bool:
        """Synchronize state with switch."""
        return await self._communicate()

    async def turn_on(self) -> bool:
        """Turn the switch on."""
        return await self._communicate(
            ON_KEY if not self._flip_on_off else OFF_KEY
        )

    async def turn_off(self) -> bool:
        """Turn the switch off."""
        return await self._communicate(
            OFF_KEY if not self._flip_on_off else ON_KEY
        )
