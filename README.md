# Introduction

This is a Python 3.8+ module aiming to interact with the Chamberlain MyQ API.

Code is licensed under the MIT license.

# [Homeassistant](https://home-assistant.io)
[Homeassistant](https://home-assistant.io) has a [core myQ component](https://www.home-assistant.io/integrations/myq/) leveraging this package.
In addition, there is also a [HACS myQ component](https://github.com/ehendrix23/hass_myq) available that can be added into HACS as a custom repository. 

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

      # Return only lamps devices:
      devices = myq.lamps
      # >>> {"serial_number123": <Device>}

      # Return only gateway devices:
      devices = myq.gateways
      # >>> {"serial_number123": <Device>}
      
      # Return *all* devices:
      devices = myq.devices
      # >>> {"serial_number123": <Device>, "serial_number456": <Device>}


asyncio.get_event_loop().run_until_complete(main())
```
## API Properties

* `accounts`: dictionary with all accounts
* `covers`: dictionary with all covers
* `devices`: dictionary with all devices  
* `gateways`: dictionary with all gateways
* `lamps`: dictionary with all lamps
* `last_state_update`: datetime (in UTC) last state update was retrieved
* `password`: password used for authentication. Can only be set, not retrieved
* `username`: username for authentication.

## Account Properties

* `id`: ID for the account
* `name`: Name of the account

## Device Properties

* `account`: Return account associated with device
* `close_allowed`: Return whether the device can be closed unattended.
* `device_family`: Return the family in which this device lives.
* `device_id`: Return the device ID (serial number).
* `device_platform`: Return the device platform.
* `device_type`: Return the device type.
* `firmware_version`: Return the family in which this device lives.
* `href`: URI for device  
* `name`: Return the device name.
* `online`: Return whether the device is online.
* `open_allowed`: Return whether the device can be opened unattended.
* `parent_device_id`: Return the device ID (serial number) of this device's parent.
* `state`: Return the current state of the device.
* `state_update`: Returns datetime when device was last updated

## API Methods

These are coroutines and need to be `await`ed – see `example.py` for examples.

* `authenticate`: Authenticate (or re-authenticate) to MyQ. Call this to
  re-authenticate immediately after changing username and/or password otherwise
  new username/password will only be used when token has to be refreshed.
* `update_device_info`: Retrieve info and status for accounts and devices


## Device Methods

All of the routines on the `MyQDevice` class are coroutines and need to be
`await`ed – see `example.py` for examples.

* `update`: get the latest device info (state, etc.). Note that 
  this runs api.update_device_info and thus all accounts/devices will be updated

## Cover Methods

All Device methods in addition to:
* `close`: close the cover
* `open`: open the cover

## Lamp Methods

All Device methods in addition to:
* `turnon`: turn lamp on
* `turnoff`: turn lamp off


# Acknowledgement

Huge thank you to [hjdhjd](https://github.com/hjdhjd) for figuring out the updated V6 API and 
sharing his work with us. 

# Disclaimer

The code here is based off of an unsupported API from
[Chamberlain](http://www.chamberlain.com/) and is subject to change without
notice. The authors claim no responsibility for damages to your garage door or
property by use of the code within.
