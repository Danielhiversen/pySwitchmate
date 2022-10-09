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

    def __init__(self, device, flip_on_off=False) -> None:
        self.available = False
        self.state = False
        self._client = None
        self._device = device
        self._flip_on_off = flip_on_off
        self._is_bright = None

    async def _connect(self, retry=True) -> bool:
        """Connect to Switchmate"""
        _LOGGER.debug("Connecting to Switchmate")
        try:
            async with CONNECT_LOCK:
                self._client = bleak.BleakClient(self._device)
                await self._client.connect()
                # "Bright" models use different handles than original models
                if self._is_bright is None:
                    self._is_bright = (
                        await self._client.read_gatt_char(21) == b"Bright"
                    )
                # Subscribing to Switchmate state notifications
                await self._client.start_notify(
                    42 if self._is_bright else 40, self._notification_handler
                )
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry:
                return await self._connect(False)
            _LOGGER.error(
                "Failed to connect to Switchmate",
                exc_info=logging.DEBUG >= _LOGGER.root.level,
            )
            self.available = False
            return False
        self.available = True
        return True

    def _notification_handler(self, _handle, data) -> None:
        _LOGGER.debug(f"Received response at {_handle} with {data}")
        self.state = data[0] != self._flip_on_off

    async def _send_command(self, key, retry=True) -> bool:
        if (
            self._client is None or not self._client.is_connected
        ) and not await self._connect():
            # No connection to Switchmate
            return False
        _LOGGER.debug("Sending key %s", key)
        try:
            async with CONNECT_LOCK:
                await self._client.write_gatt_char(
                    47 if self._is_bright else 45, key
                )
        except (bleak.BleakError, asyncio.exceptions.TimeoutError):
            if retry:
                return await self._send_command(key, False)
            _LOGGER.error(
                "Failed to send key to Switchmate",
                exc_info=logging.DEBUG >= _LOGGER.root.level,
            )
            self.available = False
            return False
        self.available = True
        return True

    async def turn_on(self) -> bool:
        """Turn the switch on."""
        return await self._send_command(
            ON_KEY if not self._flip_on_off else OFF_KEY
        )

    async def turn_off(self) -> bool:
        """Turn the switch off."""
        return await self._send_command(
            OFF_KEY if not self._flip_on_off else ON_KEY
        )
