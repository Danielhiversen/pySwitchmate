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
        self.available = False
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
            self.available = False
            return False
        self.available = True
        return True

    def _sendpacket(self, key, retry=2) -> bool:
        try:
            _LOGGER.debug("Sending key %s", key)
            self._device.writeCharacteristic(HANDLE, key, True)
        except bluepy.btle.BTLEException:
            if retry < 1 or not self._connect():
                _LOGGER.error("Cannot connect to switchmate.", exc_info=True)
                self.available = False
                return False
            return self._sendpacket(key, retry-1)
        self.available = True
        return True

    def update(self, retry=2) -> None:
        """Synchronize state with switch."""
        try:
            _LOGGER.debug("Updating device state.")
            key = ON_KEY if not self._flip_on_off else OFF_KEY
            self.state = self._device.readCharacteristic(HANDLE) == key
        except bluepy.btle.BTLEException:
            if retry < 1 or not self._connect():
                self.available = False
                _LOGGER.error("Failed to update device state.", exc_info=True)
                return None
            return self.update(retry-1)
        self.available = True
        return None

    def turn_on(self) -> bool:
        """Turn the switch on."""
        return self._sendpacket(ON_KEY if not self._flip_on_off else OFF_KEY)

    def turn_off(self) -> bool:
        """Turn the switch off."""
        return self._sendpacket(OFF_KEY if not self._flip_on_off else ON_KEY)
