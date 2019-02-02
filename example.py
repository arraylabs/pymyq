"""Run an example script to quickly test any MyQ account."""
import asyncio
import logging
import json

from aiohttp import ClientSession

import pymyq
from pymyq.device import STATE_CLOSED, STATE_OPEN
from pymyq.errors import MyQError

# Provide your email and password account details for MyQ.
MYQ_ACCOUNT_EMAIL = '<EMAIL>'
MYQ_ACCOUNT_PASSWORD = '<PASSWORD>'

# BRAND can be one of the following:
# liftmaster
# chamberlain
# craftsmaster
# merlin
MYQ_BRAND = '<BRAND>'
LOGLEVEL = 'ERROR'

# Set JSON_DUMP to True to dump all the device information retrieved,
# this can be helpful to determine what else is available.
# Set JSON_DUMP to False to open/close the doors instead. i.e.:
# JSON_DUMP = False
JSON_DUMP = True


async def main() -> None:
    """Create the aiohttp session and run the example."""

    loglevels = dict((logging.getLevelName(level), level)
                     for level in [10, 20, 30, 40, 50])

    logging.basicConfig(
        level=loglevels[LOGLEVEL],
        format='%(asctime)s:%(levelname)s:\t%(name)s\t%(message)s')

    async with ClientSession() as websession:
        try:
            myq = await pymyq.login(
                MYQ_ACCOUNT_EMAIL, MYQ_ACCOUNT_PASSWORD, MYQ_BRAND, websession)

            devices = await myq.get_devices()
            for idx, device in enumerate(devices):
                print('Device #{0}: {1}'.format(idx + 1, device.name))
                print('--------')
                print('Brand: {0}'.format(device.brand))
                print('Type: {0}'.format(device.type))
                print('Serial: {0}'.format(device.serial))
                print('Device ID: {0}'.format(device.device_id))
                print('Parent ID: {0}'.format(device.parent_id))
                print('Online: {0}'.format(device.available))
                print('Unattended Open: {0}'.format(device.open_allowed))
                print('Unattended Close: {0}'.format(device.close_allowed))
                print()
                print('Current State: {0}'.format(device.state))
                if JSON_DUMP:
                    print(json.dumps(device._device, indent=4))
                else:
                    if device.state != STATE_OPEN:
                        print('Opening the device...')
                        await device.open()
                        print('    0 Current State: {0}'.format(device.state))
                        for waited in range(1, 30):
                            if device.state == STATE_OPEN:
                                break
                            await asyncio.sleep(1)
                            await device.update()
                            print('    {} Current State: {}'.format(
                                waited, device.state))

                        await asyncio.sleep(10)
                        await device.update()
                        print()
                        print('Current State: {0}'.format(device.state))

                    if device.state != STATE_CLOSED:
                        print('Closing the device...')
                        await device.close()
                        print('    0 Current State: {0}'.format(device.state))
                        for waited in range(1, 30):
                            if device.state == STATE_CLOSED:
                                break
                            await asyncio.sleep(1)
                            await device.update()
                            print('    {} Current State: {}'.format(
                                waited, device.state))

                        await asyncio.sleep(10)
                        await device.update()
                        print()
                        print('Current State: {0}'.format(device.state))
        except MyQError as err:
            print(err)


asyncio.get_event_loop().run_until_complete(main())
