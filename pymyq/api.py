"""Define the MyQ API."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError

from .errors import MyQError, RequestError, UnsupportedBrandError

_LOGGER = logging.getLogger(__name__)

API_BASE = 'https://myqexternal.myqdevice.com'
LOGIN_ENDPOINT = "api/v4/User/Validate"
DEVICE_LIST_ENDPOINT = "api/v4/UserDeviceDetails/Get"

DEFAULT_TIMEOUT = 1
DEFAULT_REQUEST_RETRIES = 3

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=5)

DEFAULT_USER_AGENT = "Chamberlain/3.73"

BRAND_MAPPINGS = {
    'liftmaster': {
        'app_id':
        # 'Vj8pQggXLhLy0WHahglCD4N1nAkkXQtGYpq2HrHD7H1nvmbT55KqtN6RSF4ILB/i'
            'NWknvuBd7LoFHfXmKNMBcgajXtZEgKUh4V7WNzMidrpUUluDpVYVZx+xT4PCM5Kx'
    },
    'chamberlain': {
        'app_id':
            'OA9I/hgmPHFp9RYKJqCKfwnhh28uqLJzZ9KOJf1DXoo8N2XAaVX6A1wcLYyWsnnv'
    },
    'craftsman': {
        'app_id':
        # 'YmiMRRS1juXdSd0KWsuKtHmQvh5RftEp5iewHdCvsNB77FnQbY+vjCVn2nMdIeN8'
            'eU97d99kMG4t3STJZO/Mu2wt69yTQwM0WXZA5oZ74/ascQ2xQrLD/yjeVhEQccBZ'
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

    def __init__(self, brand: str, websession: ClientSession = None) -> None:
        """Initialize the API object."""
        if brand not in BRAND_MAPPINGS:
            raise UnsupportedBrandError('Unknown brand: {0}'.format(brand))

        self._brand = brand
        self._websession = websession
        self._supplied_websession = True

        self._credentials = None
        self._security_token = None
        self._devices = []
        self._last_update = None
        self.online = False

        self._update_lock = asyncio.Lock()
        self._security_token_lock = asyncio.Lock()

    def _create_websession(self):
        """Create a web session."""
        from socket import AF_INET
        from aiohttp import ClientTimeout, TCPConnector

        _LOGGER.debug('Creating web session')
        conn = TCPConnector(
            family=AF_INET,
            limit_per_host=5,
            enable_cleanup_closed=True,
        )

        # Create session object.
        session_timeout = ClientTimeout(connect=10)
        self._websession = ClientSession(connector=conn,
                                         timeout=session_timeout)
        self._supplied_websession = False

    async def close_websession(self):
        """Close web session if not already closed and created by us."""
        # We do not close the web session if it was provided.
        if self._supplied_websession or self._websession is None:
            return

        _LOGGER.debug('Closing connections')
        # Need to set _websession to none first to prevent any other task
        # from closing it as well.
        temp_websession = self._websession
        self._websession = None
        await temp_websession.close()
        await asyncio.sleep(0)
        _LOGGER.debug('Connections closed')

    async def _request(
            self,
            method: str,
            endpoint: str,
            *,
            headers: dict = None,
            params: dict = None,
            data: dict = None,
            json: dict = None,
            login_request: bool = False,
            **kwargs) -> Optional[dict]:

        # Get a security token if we do not have one AND this request
        # is not to get a security token.
        if self._security_token is None and not login_request:
            await self._get_security_token()
            if self._security_token is None:
                return None

        url = '{0}/{1}'.format(API_BASE, endpoint)

        if not headers:
            headers = {}
        if self._security_token:
            headers['SecurityToken'] = self._security_token
        headers.update({
            'MyQApplicationId': BRAND_MAPPINGS[self._brand]['app_id'],
            'User-Agent': DEFAULT_USER_AGENT,
        })

        # Create the web session if none exist.
        if self._websession is None:
            self._create_websession()

        start_request_time = datetime.time(datetime.now())
        _LOGGER.debug('%s Initiating request to %s', start_request_time, url)
        timeout = DEFAULT_TIMEOUT
        # Repeat twice amount of max requests retries for timeout errors.
        for attempt in range(0, (DEFAULT_REQUEST_RETRIES * 2) - 1):
            try:
                async with self._websession.request(
                        method, url, headers=headers, params=params,
                        data=data, json=json, timeout=timeout,
                        **kwargs) as resp:
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
            except asyncio.TimeoutError:
                # Start increasing timeout if already tried twice..
                if attempt > 1:
                    timeout = timeout * 2
                _LOGGER.debug('%s Timeout requesting from %s',
                              start_request_time, endpoint)
            except ClientError as err:
                if attempt == DEFAULT_REQUEST_RETRIES - 1:
                    raise RequestError('{} Client Error while requesting '
                                       'data from {}: {}'.format(
                                           start_request_time, endpoint,
                                           err))

                _LOGGER.warning('%s Error requesting from %s; retrying: '
                                '%s', start_request_time, endpoint, err)
                await asyncio.sleep(5)

        raise RequestError('{} Constant timeouts while requesting data '
                           'from {}'.format(start_request_time, endpoint))

    async def _update_device_state(self) -> None:
        async with self._update_lock:
            if datetime.utcnow() - self._last_update >\
                    MIN_TIME_BETWEEN_UPDATES:
                self.online = await self._get_device_states()

    async def _get_device_states(self) -> bool:
        _LOGGER.debug('Retrieving new device states')
        try:
            devices_resp = await self._request('get', DEVICE_LIST_ENDPOINT)
        except RequestError as err:
            _LOGGER.error('Getting device states failed: %s', err)
            return False

        if devices_resp is None:
            return False

        return_code = int(devices_resp.get('ReturnCode', 1))

        if return_code != 0:
            if return_code == -3333:
                # Login error, need to retrieve a new token next time.
                self._security_token = None
                _LOGGER.debug('Security token expired')
            else:
                _LOGGER.error(
                    'Error %s while retrieving states: %s',
                    devices_resp.get('ReturnCode'),
                    devices_resp.get('ErrorMessage', 'Unknown Error'))
            return False

        self._store_device_states(devices_resp.get('Devices', []))
        _LOGGER.debug('New device states retrieved')
        return True

    def _store_device_states(self, devices: dict) -> None:
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
        self._credentials = {
            'username': username,
            'password': password,
        }

        await self._get_security_token()

    async def _get_security_token(self) -> None:
        """Request a security token."""
        _LOGGER.debug('Requesting security token.')
        if self._credentials is None:
            return

        # Make sure only 1 request can be sent at a time.
        async with self._security_token_lock:
            # Confirm there is still no security token.
            if self._security_token is None:
                login_resp = await self._request(
                    'post',
                    LOGIN_ENDPOINT,
                    json=self._credentials,
                    login_request=True,
                )

                return_code = int(login_resp.get('ReturnCode', 1))
                if return_code != 0:
                    if return_code == 203:
                        # Invalid username or password.
                        _LOGGER.debug('Invalid username or password')
                        self._credentials = None
                    raise MyQError(login_resp['ErrorMessage'])

                self._security_token = login_resp['SecurityToken']

    async def get_devices(self, covers_only: bool = True) -> list:
        """Get a list of all devices associated with the account."""
        from .device import MyQDevice

        _LOGGER.debug('Retrieving list of devices')
        devices_resp = await self._request('get', DEVICE_LIST_ENDPOINT)
        # print(json.dumps(devices_resp, indent=4))

        device_list = []
        if devices_resp is None:
            return device_list

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
        websession: ClientSession = None) -> API:
    """Log in to the API."""
    api = API(brand, websession)
    await api.authenticate(username, password)
    return api
