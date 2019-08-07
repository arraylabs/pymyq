"""Define the MyQ API."""
import asyncio
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional

from aiohttp import ClientSession
from aiohttp.client_exceptions import ClientError

from .device import MyQDevice
from .errors import InvalidCredentialsError, RequestError, UnsupportedBrandError

_LOGGER = logging.getLogger(__name__)

API_VERSION = 5
API_BASE = "https://api.myqdevice.com/api/v{0}".format(API_VERSION)

DEFAULT_STATE_UPDATE_INTERVAL = timedelta(seconds=5)
DEFAULT_USER_AGENT = "Chamberlain/3.73"

NON_COVER_DEVICE_FAMILIES = "gateway"

BRAND_MAPPINGS = {
    "liftmaster": {
        "app_id": "NWknvuBd7LoFHfXmKNMBcgajXtZEgKUh4V7WNzMidrpUUluDpVYVZx+xT4PCM5Kx"
    },
    "chamberlain": {
        "app_id": "OA9I/hgmPHFp9RYKJqCKfwnhh28uqLJzZ9KOJf1DXoo8N2XAaVX6A1wcLYyWsnnv"
    },
    "craftsman": {
        "app_id": "eU97d99kMG4t3STJZO/Mu2wt69yTQwM0WXZA5oZ74/ascQ2xQrLD/yjeVhEQccBZ"
    },
    "merlin": {
        "app_id": "3004cac4e920426c823fa6c2ecf0cc28ef7d4a7b74b6470f8f0d94d6c39eb718"
    },
}


class API:  # pylint: disable=too-many-instance-attributes
    """Define a class for interacting with the MyQ iOS App API."""

    def __init__(self, brand: str, websession: ClientSession = None) -> None:
        """Initialize."""
        if brand not in BRAND_MAPPINGS:
            raise UnsupportedBrandError("Unknown brand: {0}".format(brand))

        self._account_info = {}
        self._brand = brand
        self._last_state_update = None  # type: Optional[datetime]
        self._lock = asyncio.Lock()
        self._password = None
        self._retry_security_token = False
        self._security_token = None
        self._username = None
        self._websession = websession
        self.devices = {}  # type: Dict[str, MyQDevice]

    @property
    def account_id(self) -> str:
        """Return the account ID."""
        return self._account_info["Account"]["Id"]

    @property
    def covers(self) -> Dict[str, MyQDevice]:
        """Return only those devices that are covers."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if device.device_json["device_family"] not in NON_COVER_DEVICE_FAMILIES
        }

    async def request(
        self,
        method: str,
        endpoint: str,
        *,
        headers: dict = None,
        params: dict = None,
        json: dict = None,
        login_request: bool = False,
        **kwargs
    ) -> dict:
        """Make a request."""
        url = "{0}/{1}".format(API_BASE, endpoint)

        if not headers:
            headers = {}
        if not login_request:
            headers["SecurityToken"] = self._security_token
        headers.update(
            {
                "Content-Type": "application/json",
                "MyQApplicationId": BRAND_MAPPINGS[self._brand]["app_id"],
                "User-Agent": DEFAULT_USER_AGENT,
            }
        )

        # The MyQ API can time out of multiple concurrent requests are made, so ensure
        # that only one gets through at a time:
        async with self._lock:
            async with self._websession.request(
                method, url, headers=headers, params=params, json=json, **kwargs
            ) as resp:
                data = await resp.json(content_type=None)
                try:
                    resp.raise_for_status()
                    return data
                except ClientError as err:
                    if "401" in str(err):
                        if login_request:
                            raise InvalidCredentialsError("Invalid username/password")
                        if self._retry_security_token:
                            raise RequestError(
                                "Couldn't retrieve valid security token after two tries"
                            )

                        _LOGGER.info(
                            "401 detected; attempting to get a new security token"
                        )
                        self._retry_security_token = True
                        await self.authenticate(self._username, self._password)
                        return await self.request(
                            method,
                            full_url=url,
                            headers=headers,
                            params=params,
                            json=json,
                            login_request=login_request,
                            **kwargs
                        )

                    raise RequestError(
                        "Error requesting data from {0}: {1}".format(
                            url, data["description"]
                        )
                    )

    async def authenticate(self, username: str, password: str) -> None:
        """Authenticate and get a security token."""
        self._username = username
        self._password = password

        # Retrieve and store the initial security token:
        auth_resp = await self.request(
            "post",
            "Login",
            json={"Username": username, "Password": password},
            login_request=True,
        )
        self._security_token = auth_resp["SecurityToken"]
        self._retry_security_token = False

        # Retrieve and store account info:
        self._account_info = await self.request(
            "get", "My", params={"expand": "account"}
        )

        # Retrieve and store initial set of devices:
        await self.update_device_info()

    async def update_device_info(self) -> dict:
        """Get up-to-date device info."""
        # The MyQ API can time out if state updates are too frequent; therefore,
        # throttle these requests appropriately:
        call_dt = datetime.utcnow()
        if not self._last_state_update:
            self._last_state_update = call_dt - DEFAULT_STATE_UPDATE_INTERVAL
        next_available_call_dt = self._last_state_update + DEFAULT_STATE_UPDATE_INTERVAL

        if call_dt < next_available_call_dt:
            sleep_seconds = (next_available_call_dt - call_dt).total_seconds()
            _LOGGER.debug(
                "Throttling state update for another %s seconds", sleep_seconds
            )
            await asyncio.sleep(sleep_seconds)

        devices_resp = await self.request(
            "get", "Accounts/{0}/Devices".format(self.account_id)
        )

        for device_json in devices_resp["items"]:
            serial_number = device_json["serial_number"]
            if serial_number in self.devices:
                device = self.devices[serial_number]
                device.device_json = device_json
            else:
                self.devices[device_json["serial_number"]] = MyQDevice(
                    self, device_json
                )

        self._last_state_update = datetime.utcnow()


async def login(
    username: str, password: str, brand: str, websession: ClientSession = None
) -> API:
    """Log in to the API."""
    api = API(brand, websession)
    await api.authenticate(username, password)
    return api
