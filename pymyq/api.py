"""Define the MyQ API."""
import asyncio
import logging
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Dict, Optional, Union, Tuple
from urllib.parse import urlsplit, parse_qs

from aiohttp import ClientSession, ClientResponse
from aiohttp.client_exceptions import ClientError, ClientResponseError
from pkce import generate_code_verifier, get_code_challenge

from .const import (
    ACCOUNTS_ENDPOINT,
    DEVICES_ENDPOINT,
    DEVICE_FAMILY_GARAGEDOOR,
    DEVICE_FAMILY_GATEWAY,
    DEVICE_FAMLY_LAMP,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    OAUTH_AUTHORIZE_URI,
    OAUTH_BASE_URI,
    OAUTH_TOKEN_URI,
    OAUTH_REDIRECT_URI,
)
from .device import MyQDevice
from .errors import AuthenticationError, InvalidCredentialsError, RequestError
from .garagedoor import MyQGaragedoor
from .lamp import MyQLamp
from .request import MyQRequest, REQUEST_METHODS

_LOGGER = logging.getLogger(__name__)

DEFAULT_STATE_UPDATE_INTERVAL = timedelta(seconds=20)
DEFAULT_TOKEN_REFRESH = timedelta(minutes=30)


class HTMLElementFinder(HTMLParser):
    def __init__(self, tag: str, return_attr: str, with_attr: (str, str) = None):
        self._FindTag = tag
        self._WithAttr = with_attr
        self._ReturnAttr = return_attr
        self._Result = []
        HTMLParser.__init__(self)

    @property
    def result(self):
        return self._Result

    def handle_starttag(self, tag, attrs):
        if tag == self._FindTag:
            store_attr = False
            if self._WithAttr is None:
                store_attr = True
            else:
                for attr, value in attrs:
                    if (attr, value) == self._WithAttr:
                        store_attr = True
                        break

            if store_attr:
                for attr, value in attrs:
                    if attr == self._ReturnAttr:
                        self._Result.append(value)


class API:  # pylint: disable=too-many-instance-attributes
    """Define a class for interacting with the MyQ iOS App API."""

    def __init__(
        self, username: str, password: str, websession: ClientSession = None
    ) -> None:
        """Initialize."""
        self.__credentials = {"username": username, "password": password}
        self._codeverifier = None
        self._last_state_update = None  # type: Optional[datetime]
        self._lock = asyncio.Lock()
        self._authenticate = asyncio.Lock()
        self._security_token = (
            None,
            None,
            None,
        )  # type: Tuple[Optional[str], Optional[datetime], Optional[datetime]]
        self._myqrequests = MyQRequest(websession or ClientSession())
        self.accounts = {}
        self.devices = {}  # type: Dict[str, MyQDevice]

    @property
    def covers(self) -> Dict[str, MyQGaragedoor]:
        """Return only those devices that are covers."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if device.device_json["device_family"] == DEVICE_FAMILY_GARAGEDOOR
        }

    @property
    def lamps(self) -> Dict[str, MyQDevice]:
        """Return only those devices that are covers."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if device.device_json["device_family"] == DEVICE_FAMLY_LAMP
        }

    @property
    def gateways(self) -> Dict[str, MyQDevice]:
        """Return only those devices that are covers."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if device.device_json["device_family"] == DEVICE_FAMILY_GATEWAY
        }

    @property
    def _code_verifier(self) -> str:
        if self._codeverifier is None:
            self._codeverifier = generate_code_verifier(length=43)
        return self._codeverifier

    @property
    def username(self) -> str:
        return self.__credentials["username"]

    @username.setter
    def username(self, username: str):
        self.__credentials["username"] = username

    @property
    def password(self) -> None:
        return None

    @password.setter
    def password(self, password: str):
        self.__credentials["password"] = password

    async def request(
        self,
        method: str,
        returns: str,
        url: str,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        allow_redirects: bool = True,
        login_request: bool = False,
    ) -> (ClientResponse, Union[dict, str, None]):
        """Make a request."""

        # Determine the method to call based on what is to be returned.
        call_method = REQUEST_METHODS.get(returns)
        if call_method is None:
            raise RequestError(f"Invalid return object requested: {returns}")

        call_method = getattr(self._myqrequests, call_method)

        if login_request:
            try:
                return await call_method(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    allow_redirects=allow_redirects,
                )
            except ClientResponseError as err:
                message = (
                    f"Error requesting data from {url}: {err.status} - {err.message}"
                )
                _LOGGER.error(message)
                raise RequestError(message)

            except ClientError as err:
                message = f"Error requesting data from {url}: {str(err)}"
                _LOGGER.error(message)
                raise RequestError(message)

        # Check if an authentication is in progress right now.
        if self._authenticate.locked():
            # Wait for the lock to be released before moving on.
            await self._authenticate.acquire()
            # And release it back, we just wanted to wait for it to complete.
            self._authenticate.release()

        # Check if token has to be refreshed.
        if (
            self._security_token[1] is None
            or self._security_token[1] <= datetime.utcnow()
        ):
            _LOGGER.debug(
                f"Refreshing token, last refresh was {self._security_token[2]}"
            )
            try:
                await self.authenticate()
            except RequestError as auth_err:
                message = (
                    f"Error trying to re-authenticate to myQ service: {str(auth_err)}"
                )
                _LOGGER.error(message)
                raise AuthenticationError(message)

        if not headers:
            headers = {}

        # The MyQ API can time out if multiple concurrent requests are made, so
        # ensure that only one gets through at a time.
        # Exception is when this is a login request AND there is already a lock, in that case
        # we're sending the request anyways as we know there is no active request now.

        headers["Authorization"] = self._security_token[0]

        async with self._lock:
            try:
                return await call_method(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    allow_redirects=allow_redirects,
                )
            except ClientResponseError as err:
                message = (
                    f"Error requesting data from {url}: {err.status} - {err.message}"
                )
                _LOGGER.error(message)
                raise RequestError(message)

            except ClientError as err:
                message = f"Error requesting data from {url}: {str(err)}"
                _LOGGER.error(message)
                raise RequestError(message)

    async def _oauth_authenticate(self) -> (str, int):

        # retrieve authentication page
        _LOGGER.debug("Retrieving authentication page")
        resp, text = await self.request(
            method="get",
            returns="text",
            url=OAUTH_AUTHORIZE_URI,
            headers={
                "redirect": "follow",
                "User-Agent": "null",
            },
            params={
                "client_id": OAUTH_CLIENT_ID,
                "code_challenge": get_code_challenge(self._code_verifier),
                "code_challenge_method": "S256",
                "redirect_uri": OAUTH_REDIRECT_URI,
                "response_type": "code",
                "scope": "MyQ_Residential offline_access",
            },
            login_request=True,
        )

        # Perform login to MyQ
        _LOGGER.debug("Performing login to MyQ")
        parser = HTMLElementFinder(
            tag="input",
            return_attr="value",
            with_attr=("name", "__RequestVerificationToken"),
        )

        parser.feed(text)
        request_verification_token = parser.result[0]

        resp, _ = await self.request(
            method="post",
            returns="response",
            url=resp.url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": resp.cookies.output(attrs=[]),
                "User-Agent": "null",
            },
            data={
                "Email": self.username,
                "Password": self.__credentials.get("password"),
                "__RequestVerificationToken": request_verification_token,
            },
            allow_redirects=False,
            login_request=True,
        )

        if len(resp.cookies) < 2:
            message = (
                "Invalid MyQ credentials provided. Please recheck login and password."
            )
            _LOGGER.error(message)
            raise InvalidCredentialsError(message)

        # Intercept redirect back to MyQ iOS app
        _LOGGER.debug("Calling redirect page")
        resp, _ = await self.request(
            method="get",
            returns="response",
            url=f"{OAUTH_BASE_URI}{resp.headers['Location']}",
            headers={
                "Cookie": resp.cookies.output(attrs=[]),
                "User-Agent": "null",
            },
            allow_redirects=False,
            login_request=True,
        )

        # Retrieve token
        _LOGGER.debug("Getting token")
        redirect_url = f"{OAUTH_BASE_URI}{resp.headers['Location']}"

        resp, data = await self.request(
            returns="json",
            method="post",
            url=OAUTH_TOKEN_URI,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "null",
            },
            data={
                "client_id": OAUTH_CLIENT_ID,
                "client_secret": OAUTH_CLIENT_SECRET,
                "code": parse_qs(urlsplit(redirect_url).query).get("code", ""),
                "code_verifier": self._code_verifier,
                "grant_type": "authorization_code",
                "redirect_uri": OAUTH_REDIRECT_URI,
                "scope": parse_qs(urlsplit(redirect_url).query).get(
                    "code", "MyQ_Residential offline_access"
                ),
            },
            login_request=True,
        )

        token = f"{data.get('token_type')} {data.get('access_token')}"
        try:
            expires = int(data.get('expires_in', DEFAULT_TOKEN_REFRESH))
        except ValueError:
            _LOGGER.debug(f"Expires {data.get('expires_in')} received is not an integer, using default.")
            expires = DEFAULT_TOKEN_REFRESH

        return token, expires

    async def authenticate(self) -> None:
        """Authenticate and get a security token."""
        if self.username is None or self.__credentials["password"] is None:
            _LOGGER.debug(
                "No username/password, most likely due to previous failed authentication."
            )
            return

        async with self._authenticate:
            # Retrieve and store the initial security token:
            _LOGGER.debug("Initiating OAuth authentication")
            token, expires = await self._oauth_authenticate()
            if token is None:
                _LOGGER.debug("No security token received.")
                self._security_token = (None, None, self._security_token[2])
                raise RequestError(
                    "Authentication response did not contain a security token yet one is expected."
                )

            _LOGGER.debug(f"Received token that will expire in {expires} seconds")
            self._security_token = (token, datetime.utcnow()+timedelta(seconds=int(expires/2)), datetime.now())

    async def update_device_info(self) -> Optional[dict]:
        """Get up-to-date device info."""
        # The MyQ API can time out if state updates are too frequent; therefore,
        # if back-to-back requests occur within a threshold, respond to only the first:
        call_dt = datetime.utcnow()
        if not self._last_state_update:
            self._last_state_update = call_dt - DEFAULT_STATE_UPDATE_INTERVAL
        next_available_call_dt = self._last_state_update + DEFAULT_STATE_UPDATE_INTERVAL

        if call_dt < next_available_call_dt:
            _LOGGER.debug("Ignoring device update request as it is within throttle window")
            return

        _LOGGER.debug("Updating device information, starting with retrieving accounts")
        _, accounts_resp = await self.request(
            method="get", returns="json", url=ACCOUNTS_ENDPOINT
        )
        self.accounts = {}
        if accounts_resp is not None and accounts_resp.get("accounts") is not None:
            for account in accounts_resp["accounts"]:
                account_id = account.get("id")
                if account_id is not None:
                    _LOGGER.debug(
                        f"Got account {account_id} with name {account.get('name')}"
                    )
                    self.accounts.update({account_id: account.get("name")})
        else:
            _LOGGER.debug(f"No accounts found")
            self.devices = []

        for account in self.accounts:
            _LOGGER.debug(f"Retrieving devices for account {self.accounts[account]}")
            _, devices_resp = await self.request(
                method="get",
                returns="json",
                url=DEVICES_ENDPOINT.format(account_id=account),
            )

            if devices_resp is not None and devices_resp.get("items") is not None:
                for device in devices_resp.get("items"):
                    serial_number = device.get("serial_number")
                    if serial_number is None:
                        _LOGGER.debug(
                            f"No serial number for device with name {device.get('name')}."
                        )
                        continue

                    if serial_number in self.devices:
                        _LOGGER.debug(
                            f"Updating information for device with serial number {serial_number}"
                        )
                        myqdevice = self.devices[serial_number]
                        myqdevice.device_json = device
                    else:
                        if device.get("device_family") == DEVICE_FAMILY_GARAGEDOOR:
                            _LOGGER.debug(
                                f"Adding new garage door with serial number {serial_number}"
                            )
                            self.devices[serial_number] = MyQGaragedoor(
                                api=self, account=account, device_json=device
                            )
                        elif device.get("device_family") == DEVICE_FAMLY_LAMP:
                            _LOGGER.debug(
                                f"Adding new lamp with serial number {serial_number}"
                            )
                            self.devices[serial_number] = MyQLamp(
                                api=self, account=account, device_json=device
                            )
                        elif device.get("device_family") == DEVICE_FAMILY_GATEWAY:
                            _LOGGER.debug(
                                f"Adding new gateway with serial number {serial_number}"
                            )
                            self.devices[serial_number] = MyQDevice(
                                api=self, account=account, device_json=device
                            )
                        else:
                            _LOGGER.warning(
                                f"Unknown device family {device.get('device_family')}"
                            )
            else:
                _LOGGER.debug(f"No devices found for account {self.accounts[account]}")
                self.devices = []

        self._last_state_update = datetime.utcnow()


async def login(username: str, password: str, websession: ClientSession = None) -> API:
    """Log in to the API."""

    # Set the user agent in the headers.
    api = API(username, password, websession)
    _LOGGER.debug("Performing initial authentication into MyQ")
    await api.authenticate()

    # Retrieve and store initial set of devices:
    _LOGGER.debug("Retrieving MyQ information")
    await api.update_device_info()

    return api
