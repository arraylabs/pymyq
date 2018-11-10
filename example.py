"""Run an example script to quickly test any MyQ account."""
import asyncio

from aiohttp import ClientSession

import pymyq
from pymyq.errors import MyQError


async def main() -> None:
    """Create the aiohttp session and run the example."""
    async with ClientSession() as websession:
        try:
            myq = await pymyq.login(
                '<EMAIL>', '<PASSWORD>', '<BRAND>', websession)

            devices = await myq.get_devices()
            for idx, device in enumerate(devices):
                print('Device #{0}: {1}'.format(idx + 1, device.name))
                print('--------')
                print('Brand: {0}'.format(device.brand))
                print('Type: {0}'.format(device.type))
                print('Serial: {0}'.format(device.serial))
                print('Device ID: {0}'.format(device.device_id))
                print('Parent ID: {0}'.format(device.parent_id))
                print('Current State: {0}'.format(device.state))
                print()
                print('Opening the device...')
                await device.open()
                print('Current State: {0}'.format(device.state))
                await asyncio.sleep(15)
                print('Closing the device...')
                await device.close()
                print('Current State: {0}'.format(device.state))
        except MyQError as err:
            print(err)


asyncio.get_event_loop().run_until_complete(main())
