"""Define the MyQ API."""
import asyncio
import logging
from datetime import datetime, timedelta

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError

from .device import MyQDevice
from .errors import MyQError, RequestError, UnsupportedBrandError

_LOGGER = logging.getLogger(__name__)

API_BASE = 'https://myqexternal.myqdevice.com'
LOGIN_ENDPOINT = "api/v4/User/Validate"
DEVICE_LIST_ENDPOINT = "api/v4/UserDeviceDetails/Get"

DEFAULT_TIMEOUT = 10
DEFAULT_UPDATE_RETRIES = 3

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=DEFAULT_TIMEOUT)

DEFAULT_USER_AGENT = "Chamberlain/3773 (iPhone; iOS 11.0.3; Scale/2.00)"

BRAND_MAPPINGS = {
    'liftmaster': {
        'app_id':
            'Vj8pQggXLhLy0WHahglCD4N1nAkkXQtGYpq2HrHD7H1nvmbT55KqtN6RSF4ILB/i'
    },
    'chamberlain': {
        'app_id':
            'OA9I/hgmPHFp9RYKJqCKfwnhh28uqLJzZ9KOJf1DXoo8N2XAaVX6A1wcLYyWsnnv'
    },
    'craftsman': {
        'app_id':
            'YmiMRRS1juXdSd0KWsuKtHmQvh5RftEp5iewHdCvsNB77FnQbY+vjCVn2nMdIeN8'
    },
    'merlin': {
        'app_id':
            '3004cac4e920426c823fa6c2ecf0cc28ef7d4a7b74b6470f8f0d94d6c39eb718'
    }
}

SUPPORTED_DEVICE_TYPE_NAMES = [
    'Garage Door Opener WGDO',
    'GarageDoorOpener',
    'Gate',
    'VGDO',
]


class API:
    """Define a class for interacting with the MyQ iOS App API."""

    def __init__(self, brand: str, websession: ClientSession) -> None:
        """Initialize the API object."""
        if brand not in BRAND_MAPPINGS:
            raise UnsupportedBrandError('Unknown brand: {0}'.format(brand))

        self._brand = brand
        self._security_token = None
        self._devices = []
        self._last_update = None
        self._websession = websession
        self._update_lock = asyncio.Lock()
        self._request_lock = asyncio.Lock()

    async def _request(
            self,
            method: str,
            endpoint: str,
            *,
            headers: dict = None,
            params: dict = None,
            data: dict = None,
            json: dict = None,
            **kwargs) -> dict:
        """Make a request."""
        url = '{0}/{1}'.format(API_BASE, endpoint)

        if not headers:
            headers = {}
        if self._security_token:
            headers['SecurityToken'] = self._security_token
        headers.update({
            'MyQApplicationId': BRAND_MAPPINGS[self._brand]['app_id'],
            'User-Agent': DEFAULT_USER_AGENT,
        })

        _LOGGER.debug('Initiating request to %s', url)
        async with self._request_lock:
            for attempt in range(0, DEFAULT_UPDATE_RETRIES - 1):
                try:
                    async with self._websession.request(
                            method, url, headers=headers, params=params,
                            data=data, json=json, timeout=DEFAULT_TIMEOUT,
                            **kwargs) as resp:
                        resp.raise_for_status()
                        return await resp.json(content_type=None)
                except (asyncio.TimeoutError, ClientError) as err:
                    if isinstance(err, ClientError):
                        type_exception = 'ClientError'
                    else:
                        type_exception = 'TimeOut'

                    if attempt == DEFAULT_UPDATE_RETRIES - 1:
                        raise RequestError(
                            '{} requesting data from {}: {}'.format(
                                type_exception, endpoint, err))

                    _LOGGER.warning('%s for %s; retrying: %s',
                                  type_exception, endpoint, err)
                    await asyncio.sleep(5)

        _LOGGER.debug('Request to %s completed', url)

    async def _update_device_state(self):
        async with self._update_lock:
            if datetime.utcnow() - self._last_update >\
                    MIN_TIME_BETWEEN_UPDATES:
                await self._get_device_states()

    async def _get_device_states(self):
        _LOGGER.debug('Retrieving new device states')
        try:
            devices_resp = await self._request('get', DEVICE_LIST_ENDPOINT)
        except RequestError as err:
            _LOGGER.error('Getting device states failed: %s', err)
            return False

        if int(devices_resp.get('ReturnCode', 1)) != 0:
            _LOGGER.error(
                'Error while retrieving states: %s',
                devices_resp.get('ErrorMessage', 'Unknown Error'))
            return False

        self._store_device_states(devices_resp.get('Devices', []))
        _LOGGER.debug('New device states retrieved')

    def _store_device_states(self, devices):
        for device in self._devices:
            myq_device = next(
                (element for element in devices
                 if element.get('MyQDeviceId') == device['device_id']), None)

            if myq_device is not None:
                device['device_info'] = myq_device
                continue

        self._last_update = datetime.utcnow()

    async def authenticate(self, username: str, password: str) -> None:
        """Authenticate against the API."""
        _LOGGER.debug('Starting authentication')
        login_resp = await self._request(
            'post',
            LOGIN_ENDPOINT,
            json={
                'username': username,
                'password': password
            })

        if int(login_resp['ReturnCode']) != 0:
            raise MyQError(login_resp['ErrorMessage'])

        self._security_token = login_resp['SecurityToken']
        _LOGGER.debug('Authentication completed')

    async def get_devices(self, covers_only: bool = True) -> list:
        """Get a list of all devices associated with the account."""
        _LOGGER.debug('Retrieving list of devices')
        devices_resp = await self._request('get', DEVICE_LIST_ENDPOINT)
        # print(json.dumps(devices_resp, indent=4))

        device_list = []
        for device in devices_resp['Devices']:
            if not covers_only or \
               device['MyQDeviceTypeName'] in SUPPORTED_DEVICE_TYPE_NAMES:

                self._devices.append({
                    'device_id': device['MyQDeviceId'],
                    'device_info': device
                })
                myq_device = MyQDevice(
                    self._devices[-1], self._brand, self)
                device_list.append(myq_device)

        # Store current device states.
        self._store_device_states(devices_resp.get('Devices', []))

        _LOGGER.debug('List of devices retrieved')
        return device_list


async def login(
        username: str, password: str, brand: str,
        websession: ClientSession) -> API:
    """Log in to the API."""
    api = API(brand, websession)
    await api.authenticate(username, password)
    return api
