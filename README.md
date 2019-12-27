# Introduction

This is a Python 3.5+ module aiming to interact with the Chamberlain MyQ API.

Code is licensed under the MIT license.

# Getting Started

## Installation

```python
pip install pymyq
```

## Usage

`pymyq` starts within an [aiohttp](https://aiohttp.readthedocs.io/en/stable/)
`ClientSession`:

```python
import asyncio

from aiohttp import ClientSession


async def main() -> None:
    """Create the aiohttp session and run."""
    async with ClientSession() as websession:
      # YOUR CODE HERE


asyncio.get_event_loop().run_until_complete(main())
```

To get all MyQ devices associated with an account:

```python
import asyncio

from aiohttp import ClientSession

import pymyq


async def main() -> None:
    """Create the aiohttp session and run."""
    async with ClientSession() as websession:
      myq = await pymyq.login('<EMAIL>', '<PASSWORD>', websession)

      # Return only cover devices:
      devices = myq.covers
      # >>> {"serial_number123": <Device>}

      # Return *all* devices:
      devices = myq.devices
      # >>> {"serial_number123": <Device>, "serial_number456": <Device>}


asyncio.get_event_loop().run_until_complete(main())
```

## Device Properties

* `close_allowed`: Return whether the device can be closed unattended.
* `device_family`: Return the family in which this device lives.
* `device_id`: Return the device ID (serial number).
* `device_platform`: Return the device platform.
* `device_type`: Return the device type.
* `firmware_version`: Return the family in which this device lives.
* `name`: Return the device name.
* `online`: Return whether the device is online.
* `open_allowed`: Return whether the device can be opened unattended.
* `parent_device_id`: Return the device ID (serial number) of this device's parent.
* `state`: Return the current state of the device.

## Methods

All of the routines on the `MyQDevice` class are coroutines and need to be
`await`ed – see `example.py` for examples.

* `close`: close the device
* `open`: open the device
* `update`: get the latest device info (state, etc.)

# Disclaimer

The code here is based off of an unsupported API from
[Chamberlain](http://www.chamberlain.com/) and is subject to change without
notice. The authors claim no responsibility for damages to your garage door or
property by use of the code within.
