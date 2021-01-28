"""Run an example script to quickly test."""
import asyncio
import logging

from aiohttp import ClientSession

from pymyq import login
from pymyq.errors import MyQError, RequestError

_LOGGER = logging.getLogger()

EMAIL = "<EMAIL>"
PASSWORD = "<PASSWORD>"
OPEN_CLOSE = False


def print_info(number: int, device):
    print(f"      Device {number + 1}: {device.name}")
    print(f"      Device Online: {device.online}")
    print(f"      Device ID: {device.device_id}")
    print(
        f"      Parent Device ID: {device.parent_device_id}",
    )
    print(f"      Device Family: {device.device_family}")
    print(
        f"      Device Platform: {device.device_platform}",
    )
    print(f"      Device Type: {device.device_type}")
    print(f"      Firmware Version: {device.firmware_version}")
    print(f"      Open Allowed: {device.open_allowed}")
    print(f"      Close Allowed: {device.close_allowed}")
    print(f"      Current State: {device.state}")
    print("      ---------")


async def main() -> None:
    """Create the aiohttp session and run the example."""
    logging.basicConfig(level=logging.DEBUG)
    async with ClientSession() as websession:
        try:
            # Create an API object:
            print(f"{EMAIL} {PASSWORD}")
            api = await login(EMAIL, PASSWORD, websession)

            for account in api.accounts:
                print(f"Account ID: {account}")
                print(f"Account Name: {api.accounts[account]}")

                # Get all devices listed with this account – note that you can use
                # api.covers to only examine covers or api.lamps for only lamps.
                print(f"  GarageDoors: {len(api.covers)}")
                print("  ---------------")
                if len(api.covers) != 0:
                    for idx, device_id in enumerate(
                        device_id
                        for device_id in api.covers
                        if api.devices[device_id].account == account
                    ):
                        device = api.devices[device_id]
                        print_info(number=idx, device=device)

                        if OPEN_CLOSE:
                            try:
                                if device.open_allowed:
                                    print(f"Opening garage door {device.name}")
                                    await device.open()
                                if device.open_allowed and device.close_allowed:
                                    await asyncio.sleep(15)
                                if device.close_allowed:
                                    print(f"Closing garage door {device.name}")
                                    await device.close()
                            except RequestError as err:
                                _LOGGER.error(err)
                    print("  ------------------------------")
                print(f"  Lamps: {len(api.lamps)}")
                print("  ---------")
                if len(api.lamps) != 0:
                    for idx, device_id in enumerate(
                        device_id
                        for device_id in api.lamps
                        if api.devices[device_id].account == account
                    ):
                        device = api.devices[device_id]
                        print_info(number=idx, device=device)

                        if OPEN_CLOSE:
                            try:
                                print(f"Turning lamp {device.name} on")
                                await device.turnon()
                                await asyncio.sleep(15)
                                print(f"Turning lamp {device.name} off")
                                await device.turnoff()
                            except RequestError as err:
                                _LOGGER.error(err)
                    print("  ------------------------------")

                print(f"  Gateways: {len(api.gateways)}")
                print("  ------------")
                if len(api.gateways) != 0:
                    for idx, device_id in enumerate(
                        device_id
                        for device_id in api.gateways
                        if api.devices[device_id].account == account
                    ):
                        device = api.devices[device_id]
                        print_info(number=idx, device=device)

                print("------------------------------")

        except MyQError as err:
            _LOGGER.error("There was an error: %s", err)


asyncio.get_event_loop().run_until_complete(main())
