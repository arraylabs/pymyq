"""Define the MyQ API."""
import logging

from aiohttp import BasicAuth, ClientSession
from aiohttp.client_exceptions import ClientError

from .device import MyQDevice
from .errors import MyQError, RequestError, UnsupportedBrandError

_LOGGER = logging.getLogger(__name__)

API_BASE = 'https://myqexternal.myqdevice.com'
LOGIN_ENDPOINT = "api/v4/User/Validate"
DEVICE_LIST_ENDPOINT = "api/v4/UserDeviceDetails/Get"

DEFAULT_TIMEOUT = 10
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
        self._websession = websession

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

        try:
            async with self._websession.request(
                    method, url, headers=headers, params=params, data=data,
                    json=json, timeout=DEFAULT_TIMEOUT, **kwargs) as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except ClientError as err:
            raise RequestError(
                'Error requesting data from {0}: {1}'.format(endpoint, err))

    async def authenticate(self, username: str, password: str) -> None:
        """Authenticate against the API."""
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

    async def get_devices(self, covers_only: bool = True) -> list:
        """Get a list of all devices associated with the account."""
        devices_resp = await self._request('get', DEVICE_LIST_ENDPOINT)
        return [
            MyQDevice(device, self._brand, self._request)
            for device in devices_resp['Devices'] if not covers_only
            or device['MyQDeviceTypeName'] in SUPPORTED_DEVICE_TYPE_NAMES
        ]


async def login(
        username: str, password: str, brand: str,
        websession: ClientSession) -> API:
    """Log in to the API."""
    api = API(brand, websession)
    await api.authenticate(username, password)
    return api
