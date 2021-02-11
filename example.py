"""Run an example script to quickly test."""
import asyncio
import logging

from aiohttp import ClientSession

from pymyq import login
from pymyq.errors import MyQError, RequestError
from pymyq.garagedoor import STATE_OPEN, STATE_CLOSED

_LOGGER = logging.getLogger()

EMAIL = "<EMAIL>"
PASSWORD = "<PASSWORD>"
ISSUE_COMMANDS = False


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

                        if ISSUE_COMMANDS:
                            try:
                                if device.open_allowed:
                                    if device.state == STATE_OPEN:
                                        print(
                                            f"Garage door {device.name} is already open"
                                        )
                                    else:
                                        print(f"Opening garage door {device.name}")
                                        try:
                                            if await device.open(wait_for_state=True):
                                                print(
                                                    f"Garage door {device.name} has been opened."
                                                )
                                            else:
                                                print(
                                                    f"Failed to open garage door {device.name}."
                                                )
                                        except MyQError as err:
                                            _LOGGER.error(
                                                f"Error when trying to open {device.name}: {str(err)}"
                                            )
                                else:
                                    print(
                                        f"Opening of garage door {device.name} is not allowed."
                                    )

                                if device.close_allowed:
                                    if device.state == STATE_CLOSED:
                                        print(
                                            f"Garage door {device.name} is already closed"
                                        )
                                    else:
                                        print(f"Closing garage door {device.name}")
                                        try:
                                            wait_task = await device.close(
                                                wait_for_state=False
                                            )
                                        except MyQError as err:
                                            _LOGGER.error(
                                                f"Error when trying to close {device.name}: {str(err)}"
                                            )

                                        print(f"Device {device.name} is {device.state}")

                                        if await wait_task:
                                            print(
                                                f"Garage door {device.name} has been closed."
                                            )
                                        else:
                                            print(
                                                f"Failed to close garage door {device.name}."
                                            )

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

                        if ISSUE_COMMANDS:
                            try:
                                print(f"Turning lamp {device.name} on")
                                await device.turnon(wait_for_state=True)
                                await asyncio.sleep(5)
                                print(f"Turning lamp {device.name} off")
                                await device.turnoff(wait_for_state=True)
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
