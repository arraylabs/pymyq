"""Handle requests to MyQ."""
import asyncio
from datetime import datetime, timedelta
from json import JSONDecodeError
import logging
from random import choices
import string
from typing import Optional, Tuple

from aiohttp import ClientResponse, ClientSession
from aiohttp.client_exceptions import ClientError, ClientResponseError

from .errors import RequestError

_LOGGER = logging.getLogger(__name__)

REQUEST_METHODS = dict(
    json="request_json", text="request_text", response="request_response"
)
DEFAULT_REQUEST_RETRIES = 5
USER_AGENT_REFRESH = timedelta(hours=1)


class MyQRequest:  # pylint: disable=too-many-instance-attributes
    """Define a class to handle requests to MyQ"""

    def __init__(self, websession: ClientSession = None) -> None:
        self._websession = websession or ClientSession()
        self._useragent = None
        self._last_useragent_update = None

    async def _get_useragent(self) -> None:
        """Retrieve a user agent to use in headers."""

        # Only see to retrieve a user agent if currently we do not have one,
        # we do not have an datetime on when we last retrieved one,
        # or we're passed the minimum time between requests.
        if (
            self._useragent is not None
            and self._last_useragent_update is not None
            and self._last_useragent_update + USER_AGENT_REFRESH > datetime.utcnow()
        ):
            _LOGGER.debug(
                "Ignoring user agent update request as it is within throttle window"
            )
            return

        self._last_useragent_update = datetime.utcnow()

        # Retrieve user agent from GitHub if not provided for login.
        _LOGGER.debug("Retrieving user agent from GitHub.")
        url = "https://raw.githubusercontent.com/arraylabs/pymyq/master/.USER_AGENT"

        try:
            async with ClientSession() as session:
                async with session.get(url) as resp:
                    useragent = await resp.text()
                    resp.raise_for_status()
                    _LOGGER.debug("Retrieved user agent %s from GitHub.", useragent)

        except ClientError as exc:
            # Default user agent to random string with length of 5
            # if failure to retrieve it from GitHub.
            useragent = "#RANDOM:5"
            _LOGGER.warning(
                "Failed retrieving user agent from GitHub, will use randomized user agent "
                "instead: %s",
                str(exc),
            )

        useragent = useragent.strip()
        # Check if value for useragent is to create a random user agent.
        useragent_list = useragent.split(":")
        if useragent_list[0] == "#RANDOM":
            # Create a random string, check if length is provided for the random string,
            # if not then default is 5.
            try:
                randomlength = int(useragent_list[1]) if len(useragent_list) == 2 else 5
            except ValueError:
                _LOGGER.debug(
                    "Random length value %s in user agent %s is not an integer. "
                    "Setting to 5 instead.",
                    useragent_list[1],
                    useragent,
                )
                randomlength = 5

            # Create the random user agent.
            useragent = "".join(
                choices(string.ascii_letters + string.digits, k=randomlength)
            )
            _LOGGER.debug("User agent set to randomized value: %s.", useragent)

        self._useragent = useragent

    async def _send_request(
        self,
        method: str,
        url: str,
        websession: ClientSession,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        allow_redirects: bool = False,
    ) -> Optional[ClientResponse]:

        attempt = 0
        resp = None
        resp_exc = None
        last_status = ""
        last_error = ""

        for attempt in range(DEFAULT_REQUEST_RETRIES):
            if self._useragent is None:
                await self._get_useragent()

            if self._useragent is not None and self._useragent != "":
                headers.update({"User-Agent": self._useragent})

            if attempt != 0:
                wait_for = min(2 ** attempt, 5)
                _LOGGER.debug(
                    'Request failed with "%s %s" (attempt #%s/%s)"; trying again in %s seconds',
                    last_status,
                    last_error,
                    attempt,
                    DEFAULT_REQUEST_RETRIES,
                    wait_for,
                )
                await asyncio.sleep(wait_for)

            try:
                _LOGGER.debug(
                    "Sending myq api request %s and headers %s with connection pooling",
                    url,
                    headers,
                )
                resp = await websession.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json,
                    skip_auto_headers={"USER-AGENT"},
                    allow_redirects=allow_redirects,
                    raise_for_status=True,
                )

                _LOGGER.debug("Response:")
                _LOGGER.debug("    Response Code: %s", resp.status)
                _LOGGER.debug("    Headers: %s", resp.raw_headers)
                _LOGGER.debug("    Body: %s", await resp.text())
                return resp
            except ClientResponseError as err:
                _LOGGER.debug(
                    "Attempt %s request failed with exception : %s - %s",
                    attempt + 1,
                    err.status,
                    err.message,
                )
                if err.status == 401:
                    raise err

                last_status = err.status
                last_error = err.message
                resp_exc = err

                if err.status == 400 and attempt == 0:
                    _LOGGER.debug(
                        "Received error status 400, bad request. Will refresh user agent."
                    )
                    await self._get_useragent()

            except ClientError as err:
                _LOGGER.debug(
                    "Attempt %s request failed with exception: %s", attempt, str(err)
                )
                last_status = ""
                last_error = str(err)
                resp_exc = err

        if resp_exc is not None:
            raise resp_exc

        return resp

    async def request_json(
        self,
        method: str,
        url: str,
        websession: ClientSession = None,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        allow_redirects: bool = False,
    ) -> Tuple[Optional[ClientResponse], Optional[dict]]:
        """Send request and retrieve json response

        Args:
            method (str): [description]
            url (str): [description]
            websession (ClientSession, optional): [description]. Defaults to None.
            headers (dict, optional): [description]. Defaults to None.
            params (dict, optional): [description]. Defaults to None.
            data (dict, optional): [description]. Defaults to None.
            json (dict, optional): [description]. Defaults to None.
            allow_redirects (bool, optional): [description]. Defaults to False.

        Raises:
            RequestError: [description]

        Returns:
            Tuple[Optional[ClientResponse], Optional[dict]]: [description]
        """

        websession = websession or self._websession
        json_data = None

        resp = await self._send_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            allow_redirects=allow_redirects,
            websession=websession,
        )

        if resp is not None:
            try:
                json_data = await resp.json(content_type=None)
            except JSONDecodeError as err:
                message = (
                    f"JSON Decoder error {err.msg} in response at line {err.lineno}"
                    f" column {err.colno}. Response received was:\n{err.doc}"
                )
                _LOGGER.error(message)
                raise RequestError(message) from err

        return resp, json_data

    async def request_text(
        self,
        method: str,
        url: str,
        websession: ClientSession = None,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        allow_redirects: bool = False,
    ) -> Tuple[Optional[ClientResponse], Optional[str]]:
        """Send request and retrieve text

        Args:
            method (str): [description]
            url (str): [description]
            websession (ClientSession, optional): [description]. Defaults to None.
            headers (dict, optional): [description]. Defaults to None.
            params (dict, optional): [description]. Defaults to None.
            data (dict, optional): [description]. Defaults to None.
            json (dict, optional): [description]. Defaults to None.
            allow_redirects (bool, optional): [description]. Defaults to False.

        Returns:
            Tuple[Optional[ClientResponse], Optional[str]]: [description]
        """

        websession = websession or self._websession
        data_text = None
        resp = await self._send_request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            data=data,
            json=json,
            allow_redirects=allow_redirects,
            websession=websession,
        )

        if resp is not None:
            data_text = await resp.text()

        return resp, data_text

    async def request_response(
        self,
        method: str,
        url: str,
        websession: ClientSession = None,
        headers: dict = None,
        params: dict = None,
        data: dict = None,
        json: dict = None,
        allow_redirects: bool = False,
    ) -> Tuple[Optional[ClientResponse], None]:
        """Send request and just receive the ClientResponse object

        Args:
            method (str): [description]
            url (str): [description]
            websession (ClientSession, optional): [description]. Defaults to None.
            headers (dict, optional): [description]. Defaults to None.
            params (dict, optional): [description]. Defaults to None.
            data (dict, optional): [description]. Defaults to None.
            json (dict, optional): [description]. Defaults to None.
            allow_redirects (bool, optional): [description]. Defaults to False.

        Returns:
            Tuple[Optional[ClientResponse], None]: [description]
        """

        websession = websession or self._websession

        return (
            await self._send_request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json,
                allow_redirects=allow_redirects,
                websession=websession,
            ),
            None,
        )
