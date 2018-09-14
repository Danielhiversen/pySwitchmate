"""Library to handle connection with Switchmate"""

import logging

import bluepy

HANDLE = 0x2e
ON_KEY = b'\x01'
OFF_KEY = b'\x00'

_LOGGER = logging.getLogger(__name__)


class Switchmate:
    """Representation of a Switchmate."""

    def __init__(self, mac, flip_on_off=False) -> None:
        self._mac = mac
        self.state = False
        self._device = None
        self._flip_on_off = flip_on_off
        self._connect()

    def _connect(self) -> bool:
        if self._device is not None:
            _LOGGER.debug("Disconnecting")
            try:
                self._device.disconnect()
            except bluepy.btle.BTLEException:
                pass
        try:
            _LOGGER.debug("Connecting")
            self._device = bluepy.btle.Peripheral(self._mac,
                                                  bluepy.btle.ADDR_TYPE_RANDOM)
        except bluepy.btle.BTLEException:
            _LOGGER.error("Failed to connect to switchmate", exc_info=True)
            return False
        return True

    def _sendpacket(self, key, retry=2) -> bool:
        try:
            _LOGGER.debug("Sending key %s", key)
            self._device.writeCharacteristic(HANDLE, key, True)
        except bluepy.btle.BTLEException:
            if retry < 1:
                _LOGGER.error("Cannot connect to switchmate.")
                return False
            _LOGGER.error("Cannot connect to switchmate. Retrying")
            if not self._connect():
                return False
            return self._sendpacket(key, retry-1)
        return True

    def update(self) -> None:
        """Synchronize state with switch."""
        try:
            _LOGGER.debug("Updating device state.")
            key = ON_KEY if not self._flip_on_off else OFF_KEY
            self.state = self._device.readCharacteristic(HANDLE) == key
        except bluepy.btle.BTLEException:
            _LOGGER.error("Failed to update device state.", exc_info=True)
            self._connect()

    def turn_on(self) -> bool:
        """Turn the switch on."""
        return self._sendpacket(ON_KEY if not self._flip_on_off else OFF_KEY)

    def turn_off(self) -> bool:
        """Turn the switch off."""
        return self._sendpacket(OFF_KEY if not self._flip_on_off else ON_KEY)
