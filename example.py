"""Run an example script to quickly test."""
import asyncio
import logging

from aiohttp import ClientSession

from pymyq import login
from pymyq.errors import MyQError, RequestError

_LOGGER = logging.getLogger()

EMAIL = "<EMAIL>"
PASSWORD = "<PASSWORD>"


async def main() -> None:
    """Create the aiohttp session and run the example."""
    logging.basicConfig(level=logging.INFO)
    async with ClientSession() as websession:
        try:
            # Create an API object:
            api = await login(EMAIL, PASSWORD, websession)

            # Get the account ID:
            _LOGGER.info("Account ID: %s", api.account_id)

            # Get all devices listed with this account – note that you can use
            # api.covers to only examine covers:
            for idx, device_id in enumerate(api.devices):
                device = api.devices[device_id]
                _LOGGER.info("---------")
                _LOGGER.info("Device %s: %s", idx + 1, device.name)
                _LOGGER.info("Device Online: %s", device.online)
                _LOGGER.info("Device ID: %s", device.device_id)
                _LOGGER.info("Parent Device ID: %s", device.parent_device_id)
                _LOGGER.info("Device Family: %s", device.device_family)
                _LOGGER.info("Device Platform: %s", device.device_platform)
                _LOGGER.info("Device Type: %s", device.device_type)
                _LOGGER.info("Firmware Version: %s", device.firmware_version)
                _LOGGER.info("Open Allowed: %s", device.open_allowed)
                _LOGGER.info("Close Allowed: %s", device.close_allowed)
                _LOGGER.info("Current State: %s", device.state)

                try:
                    await device.open()
                    await asyncio.sleep(15)
                    await device.close()
                except RequestError as err:
                    _LOGGER.error(err)
        except MyQError as err:
            _LOGGER.error("There was an error: %s", err)


asyncio.get_event_loop().run_until_complete(main())
