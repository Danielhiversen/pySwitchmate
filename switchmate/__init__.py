"""Library to handle connection with Switchmate"""

import bluepy
import logging
import sys

from enum import Enum

from bluepy.btle import (Scanner, AssignedNumbers, BTLEException)

# Values known to work on current FW
# https://github.com/brianpeiris/switchmate/issues/6#issuecomment-366395303
# Bright/Slim (Slim Device with Motion Sensor): FW v2.9.15+
# Light/Original/Switchmate (No Motion Sensor): FW v2.99.18+

BRIGHT_STATE_HANDLE = 0x30
ORIGINAL_MODEL_STRING_HANDLE = 0x14
ORIGINAL_STATE_HANDLE = 0x2e
SERVICES_AD_TYPE = 0x07
SWITCHMATE_SERVICE = "a22bd383-ebdd-49ac-b2e7-40eb55f5d0ab"

ON_KEY = b"\x01"
OFF_KEY = b"\x00"

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(
    logging.StreamHandler(sys.stdout))
_LOGGER.setLevel(logging.DEBUG)


class Model(Enum):
    ORIGINAL = 1
    BRIGHT = 2


def _get_switchmates(scan_entries):
    switchmates = []
    for scan_entry in scan_entries:
        service_uuid = scan_entry.getValueText(SERVICES_AD_TYPE)
        is_switchmate = service_uuid == SWITCHMATE_SERVICE
        if not is_switchmate:
            continue
        if not list(
            filter(lambda sw: (sw.mac == scan_entry.addr), switchmates)
        ):
            switchmates.append(Switchmate(mac=scan_entry.addr))
    switchmates.sort(key=lambda sw: sw.mac)
    return switchmates


def scan(timeout=None):
    scanner = Scanner()

    try:
        switchmates = _get_switchmates(scanner.scan(timeout))
    except (BTLEException):
        _LOGGER.error(
            "Could not complete scan. Try running switchmate with sudo.",
            exc_info=logging.DEBUG >= _LOGGER.root.level)
        return
    except (OSError):
        _LOGGER.error(
            "Could not complete scan. Try compiling the bluepy helper.",
            exc_info=logging.DEBUG >= _LOGGER.root.level)
        return

    if len(switchmates):
        _LOGGER.debug("Found %s devices", len(switchmates))
    else:
        _LOGGER.debug("No Switchmate devices found")

    sys.stdout.flush()
    return switchmates


class Switchmate:
    """Representation of a Switchmate."""

    def __init__(self, mac, flip_on_off=False) -> None:
        self.available = False
        self.battery = 0
        self.mac = mac
        self.model = None
        self.state = False
        self._device = None
        self._flip_on_off = flip_on_off

    def _getHandle(self) -> str:
        if self.model is Model.ORIGINAL:
            return ORIGINAL_STATE_HANDLE
        else:
            return BRIGHT_STATE_HANDLE

    def _connect(self, retry=10) -> bool:
        if self._device is not None:
            _LOGGER.debug("Disconnecting")
            try:
                self._device.disconnect()
            except bluepy.btle.BTLEException:
                pass
        try:
            _LOGGER.debug("Connecting")
            self._device = bluepy.btle.Peripheral(self.mac,
                                                  bluepy.btle.ADDR_TYPE_RANDOM)
        except (bluepy.btle.BTLEException, BrokenPipeError, AttributeError):
            if retry < 1:
                _LOGGER.error("Failed to connect to switchmate",
                              exc_info=logging.DEBUG >= _LOGGER.root.level)
                self.available = False
                return False
            return self._connect(retry-1)
        self.available = True
        return True

    def _sendpacket(self, key, retry=10) -> bool:
        try:
            _LOGGER.debug("Sending key %s", key)
            self._device.writeCharacteristic(self._getHandle(), key, True)
        except (bluepy.btle.BTLEException, BrokenPipeError, AttributeError):
            if retry < 1 or not self._connect():
                _LOGGER.error("Cannot connect to switchmate.",
                              exc_info=logging.DEBUG >= _LOGGER.root.level)
                self.available = False
                return False
            return self._sendpacket(key, retry-1)
        self.available = True
        return True

    def update(self, retry=10) -> None:
        """Synchronize state with switch."""
        try:
            _LOGGER.debug("Updating device state.")

            # Device State
            key = ON_KEY if not self._flip_on_off else OFF_KEY
            self.state = self._device.readCharacteristic(
                self._getHandle()) == key

            # Battery Level
            battery_level = AssignedNumbers.batteryLevel
            self.battery = self._device.getCharacteristics(uuid=battery_level)[
                0].read()

            # The handle for reading the model string on Bright devices is actually
            # different from Original devices, but using getCharacteristics to read
            # the model is much slower.
            if self._device.readCharacteristic(ORIGINAL_MODEL_STRING_HANDLE):
                self.model = Model.ORIGINAL
            else:
                self.model = Model.BRIGHT

        except (bluepy.btle.BTLEException, AttributeError):
            if retry < 1 or not self._connect():
                self.available = False
                _LOGGER.error("Failed to update device state.", exc_info=True)
                return None
            return self.update(retry-1)
        self.available = True

        _LOGGER.debug("Processing device %s", self.mac)
        _LOGGER.debug("Model %s", self.model)
        _LOGGER.debug("State %s", self.state)
        _LOGGER.debug("Battery %s", ord(self.battery))

        return None

    def turn_on(self) -> bool:
        """Turn the switch on."""
        return self._sendpacket(ON_KEY if not self._flip_on_off else OFF_KEY)

    def turn_off(self) -> bool:
        """Turn the switch off."""
        return self._sendpacket(OFF_KEY if not self._flip_on_off else ON_KEY)
