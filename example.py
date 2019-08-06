"""Run an example script to quickly test."""
import asyncio
import logging

from aiohttp import ClientSession

from pymyq import login
from pymyq.errors import MyQError

_LOGGER = logging.getLogger()

EMAIL = "<EMAIL ADDRESS>"
PASSWORD = "<PASSWORD>"
BRAND = "chamberlain"


async def main() -> None:
    """Create the aiohttp session and run the example."""
    logging.basicConfig(level=logging.INFO)
    async with ClientSession() as websession:
        try:
            # Create an API object:
            api = await login(EMAIL, PASSWORD, BRAND, websession)

            # Get the account ID:
            _LOGGER.info("Account ID: %s", api.account_id)

            # Get all devices listed with this account:
            for cover in api.covers.values():
                await cover.open()
        except MyQError as err:
            _LOGGER.error("There was an error: %s", err)


asyncio.get_event_loop().run_until_complete(main())
