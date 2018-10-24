"""Define a generic MyQ device."""
import asyncio
import logging
from typing import Callable, Union

from .errors import RequestError

_LOGGER = logging.getLogger(__name__)

DEFAULT_UPDATE_RETRIES = 3

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

    def __init__(
            self, device_json: dict, brand: str, request: Callable) -> None:
        """Initialize."""
        self._brand = brand
        self._device_json = device_json
        self._request = request

        try:
            raw_state = next(
                attr['Value'] for attr in device_json['Attributes']
                if attr['AttributeDisplayName'] == 'doorstate')

            self._state = self._coerce_state_from_string(raw_state)
        except StopIteration:
            self._state = STATE_UNKNOWN

    @property
    def brand(self) -> str:
        """Return the brand of this device."""
        return self._brand

    @property
    def device_id(self) -> int:
        """Return the device ID."""
        return self._device_json['MyQDeviceId']

    @property
    def parent_id(self) -> Union[None, int]:
        """Return the ID of the parent device (if it exists)."""
        return self._device_json.get('ParentMyQDeviceId')

    @property
    def name(self) -> str:
        """Return the device name."""
        return next(
            attr['Value'] for attr in self._device_json['Attributes']
            if attr['AttributeDisplayName'] == 'desc')

    @property
    def serial(self) -> str:
        """Return the device serial number."""
        return self._device_json['SerialNumber']

    @property
    def state(self) -> str:
        """Return the current state of the device (if it exists)."""
        return self._state

    @property
    def type(self) -> str:
        """Return the device type."""
        return self._device_json['MyQDeviceTypeName']

    @staticmethod
    def _coerce_state_from_string(value: Union[int, str]) -> str:
        """Return a proper state from a string input."""
        try:
            return STATE_MAP[int(value)]
        except KeyError:
            _LOGGER.error('Unknown state: %s', value)
            return STATE_UNKNOWN

    async def _set_state(self, state: int) -> bool:
        """Set the state of the device."""
        for attempt in range(0, DEFAULT_UPDATE_RETRIES - 1):
            try:
                set_state_resp = await self._request(
                    'put',
                    DEVICE_SET_ENDPOINT,
                    json={
                        'attributeName': 'desireddoorstate',
                        'myQDeviceId': self.device_id,
                        'AttributeValue': state,
                    })

                break
            except RequestError as err:
                if attempt == DEFAULT_UPDATE_RETRIES - 1:
                    _LOGGER.error('Setting state failed (and halting): %s',
                                  err)
                    return False

                _LOGGER.error('Setting state failed; retrying')
                await asyncio.sleep(4)

        if int(set_state_resp['ReturnCode']) != 0:
            _LOGGER.error(
                'There was an error while setting the device state: %s',
                set_state_resp['ErrorMessage'])
            return False

        return True

    async def close(self) -> None:
        """Close the device."""
        return await self._set_state(0)

    async def open(self) -> None:
        """Open the device."""
        return await self._set_state(1)

    async def update(self) -> bool:
        """Update the device info from the MyQ cloud."""
        for attempt in range(0, DEFAULT_UPDATE_RETRIES - 1):
            try:
                update_resp = await self._request(
                    'get',
                    DEVICE_ATTRIBUTE_GET_ENDPOINT,
                    params={
                        'AttributeName': 'doorstate',
                        'MyQDeviceId': self.device_id
                    })

                break
            except RequestError as err:
                if attempt == DEFAULT_UPDATE_RETRIES - 1:
                    _LOGGER.error('Update failed (and halting): %s', err)
                    return False

                _LOGGER.error('Update failed; retrying')
                await asyncio.sleep(4)

        if int(update_resp['ReturnCode']) != 0:
            _LOGGER.error(
                'There was an error while updating: %s',
                update_resp['ErrorMessage'])
            return False

        self._state = self._coerce_state_from_string(
            update_resp['AttributeValue'])

        return True
