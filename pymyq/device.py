"""Define a generic MyQ device."""
import logging
from datetime import datetime, timedelta
from typing import Union

from .api import API
from .errors import RequestError

_LOGGER = logging.getLogger(__name__)

DEVICE_ATTRIBUTE_GET_ENDPOINT = "api/v4/DeviceAttribute/getDeviceAttribute"
DEVICE_SET_ENDPOINT = "api/v4/DeviceAttribute/PutDeviceAttribute"

STATE_OPEN = 'open'
STATE_CLOSED = 'closed'
STATE_STOPPED = 'stopped'
STATE_OPENING = 'opening'
STATE_CLOSING = 'closing'
STATE_UNKNOWN = 'unknown'
STATE_TRANSITION = 'transition'

STATE_MAP = {
    1: STATE_OPEN,
    2: STATE_CLOSED,
    3: STATE_STOPPED,
    4: STATE_OPENING,
    5: STATE_CLOSING,
    6: STATE_UNKNOWN,
    7: STATE_UNKNOWN,
    8: STATE_TRANSITION,
    9: STATE_OPEN,
    0: STATE_UNKNOWN
}


class MyQDevice:
    """Define a generic MyQ device."""

    def __init__(self, device: dict, brand: str, api: API) -> None:
        """Initialize."""
        self._brand = brand
        self._device = device
        self._device_json = device['device_info']
        self._device_id = self._device_json['MyQDeviceId']
        self.api = api
        self.next_allowed_update = None

    @property
    def brand(self) -> str:
        """Return the brand of this device."""
        return self._brand

    @property
    def device_id(self) -> int:
        """Return the device ID."""
        return self._device_id

    @property
    def parent_id(self) -> Union[None, int]:
        """Return the ID of the parent device (if it exists)."""
        return self._device_json.get('ParentMyQDeviceId')

    @property
    def name(self) -> str:
        """Return the device name."""
        return next(
            attr['Value'] for attr in self._device_json.get('Attributes', [])
            if attr.get('AttributeDisplayName') == 'desc')

    @property
    def available(self) -> bool:
        """Return if device is online or not."""
        # Both ability to retrieve state from MyQ cloud AND device itself has
        # to be online.
        is_available = self.api.online and \
            next(
                attr['Value'] for attr in
                self._device_json.get('Attributes', [])
                if attr.get('AttributeDisplayName') == 'online') == "True"

        return is_available

    @property
    def serial(self) -> str:
        """Return the device serial number."""
        return self._device_json.get('SerialNumber')

    @property
    def open_allowed(self) -> bool:
        """Door can be opened unattended."""
        return next(
            attr['Value'] for attr in self._device_json.get('Attributes', [])
            if attr.get('AttributeDisplayName') == 'isunattendedopenallowed')\
            == "1"

    @property
    def close_allowed(self) -> bool:
        """Door can be closed unattended."""
        return next(
            attr['Value'] for attr in self._device_json.get('Attributes', [])
            if attr.get('AttributeDisplayName') == 'isunattendedcloseallowed')\
            == "1"

    @property
    def state(self) -> str:
        """Return the current state of the device (if it exists)."""
        return self._coerce_state_from_string(
            next(
                attr['Value'] for attr in self._device_json.get(
                    'Attributes', [])
                if attr.get('AttributeDisplayName') == 'doorstate'))

    def _update_state(self, value: str) -> None:
        """Update state temporary during open or close."""
        attribute = next(attr for attr in self._device['device_info'].get(
            'Attributes', []) if attr.get(
                'AttributeDisplayName') == 'doorstate')
        if attribute is not None:
            attribute['Value'] = value

    @property
    def type(self) -> str:
        """Return the device type."""
        return self._device_json.get('MyQDeviceTypeName')

    @staticmethod
    def _coerce_state_from_string(value: Union[int, str]) -> str:
        """Return a proper state from a string input."""
        try:
            return STATE_MAP[int(value)]
        except KeyError:
            _LOGGER.error('Unknown state: %s', value)
            return STATE_UNKNOWN

    # pylint: disable=protected-access
    async def _set_state(self, state: int) -> bool:
        """Set the state of the device."""
        try:
            set_state_resp = await self.api._request(
                'put',
                DEVICE_SET_ENDPOINT,
                json={
                    'attributeName': 'desireddoorstate',
                    'myQDeviceId': self.device_id,
                    'AttributeValue': state,
                })
        except RequestError as err:
            _LOGGER.error('%s: Setting state failed (and halting): %s',
                          self.name, err)
            return False

        if set_state_resp is None:
            return False

        if int(set_state_resp.get('ReturnCode', 1)) != 0:
            _LOGGER.error(
                '%s: Error setting the device state: %s', self.name,
                set_state_resp.get('ErrorMessage', 'Unknown Error'))
            return False

        return True

    async def close(self) -> bool:
        """Close the device."""
        _LOGGER.debug('%s: Sending close command', self.name)
        if not await self._set_state(0):
            return False

        # Do not allow update of this device's state for 10 seconds.
        self.next_allowed_update = datetime.utcnow() + timedelta(seconds=10)

        # Ensure state is closed or closing.
        if self.state not in (STATE_CLOSED, STATE_CLOSING):
            # Set state to closing.
            self._update_state('5')
            self._device_json = self._device['device_info']

        _LOGGER.debug('%s: Close command send', self.name)
        return True

    async def open(self) -> bool:
        """Open the device."""
        _LOGGER.debug('%s: Sending open command', self.name)
        if not await self._set_state(1):
            return False

        # Do not allow update of this device's state for 5 seconds.
        self.next_allowed_update = datetime.utcnow() + timedelta(seconds=5)

        # Ensure state is open or opening
        if self.state not in (STATE_OPEN, STATE_OPENING):
            # Set state to opening
            self._update_state('4')
            self._device_json = self._device['device_info']

        _LOGGER.debug('%s: Open command send', self.name)
        return True

    # pylint: disable=protected-access
    async def update(self) -> None:
        """Retrieve updated device state."""
        if self.next_allowed_update is not None and \
                datetime.utcnow() < self.next_allowed_update:
            return

        self.next_allowed_update = None
        await self.api._update_device_state()
        self._device_json = self._device['device_info']

    async def close_connection(self):
        """Close the web session connection with MyQ"""
        await self.api.close_websession()
