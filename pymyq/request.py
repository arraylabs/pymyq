"""Handle requests to MyQ."""
import asyncio
import logging
from json import JSONDecodeError

from aiohttp import ClientSession, ClientResponse
from aiohttp.client_exceptions import ClientError, ClientResponseError

from .errors import RequestError

_LOGGER = logging.getLogger(__name__)

REQUEST_METHODS = dict(
    json="request_json", text="request_text", response="request_response"
)
DEFAULT_REQUEST_RETRIES = 5


class MyQRequest:  # pylint: disable=too-many-instance-attributes
    """Define a class to handle requests to MyQ"""

    def __init__(self, websession: ClientSession = None, useragent: str = None) -> None:
        self._websession = websession or ClientSession()
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
    ) -> ClientResponse:

        attempt = 0
        resp_exc = None
        last_status = ""
        last_error = ""

        if self._useragent is not None:
            headers.update({"User-Agent": self._useragent})

        while attempt < DEFAULT_REQUEST_RETRIES:
            if attempt != 0:
                wait_for = min(2 ** attempt, 5)
                _LOGGER.debug(
                    f'Request failed with "{last_status} {last_error}" '
                    f'(attempt #{attempt}/{DEFAULT_REQUEST_RETRIES})"; trying again in {wait_for} seconds'
                )
                await asyncio.sleep(wait_for)

            attempt += 1
            try:
                _LOGGER.debug(
                    f"Sending myq api request {url} and headers {headers} with connection pooling"
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
                _LOGGER.debug(f"    Response Code: {resp.status}")
                _LOGGER.debug(f"    Headers: {resp.raw_headers}")
                _LOGGER.debug(f"    Body: {await resp.text()}")
                return resp
            except ClientResponseError as err:
                _LOGGER.debug(
                    f"Attempt {attempt} request failed with exception : {err.status} - {err.message}"
                )
                if err.status == 401:
                    raise err
                last_status = err.status
                last_error = err.message
                resp_exc = err
            except ClientError as err:
                _LOGGER.debug(
                    f"Attempt {attempt} request failed with exception:: {str(err)}"
                )
                last_status = ""
                last_error = str(err)
                resp_exc = err

        raise resp_exc

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
    ) -> (ClientResponse, dict):

        websession = websession or self._websession

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

        try:
            data = await resp.json(content_type=None)
        except JSONDecodeError as err:
            message = (
                f"JSON Decoder error {err.msg} in response at line {err.lineno} column {err.colno}. Response "
                f"received was:\n{err.doc}"
            )
            _LOGGER.error(message)
            raise RequestError(message)

        return resp, data

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
    ) -> (ClientResponse, str):

        websession = websession or self._websession

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

        return resp, await resp.text()

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
    ) -> (ClientResponse, None):

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
