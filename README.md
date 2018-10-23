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
      # Valid Brands: 'chamberlain', 'craftsman', 'liftmaster', 'merlin'
      myq = await pymyq.login('<EMAIL>', '<PASSWORD>', '<BRAND>', websession)

      # Return only cover devices:
      devices = await myq.get_devices()

      # Return *all* devices:
      devices = await myq.get_devices(covers_only=False)


asyncio.get_event_loop().run_until_complete(main())
```

## Device Properties

* `brand`: the brand of the device
* `device_id`: the device's MyQ ID
* `parent_id`: the device's parent device's MyQ ID
* `name`: the name of the device
* `serial`: the serial number of the device
* `state`: the device's current state
* `type`: the type of MyQ device

## Methods

All of the routines on the `MyQDevice` class are coroutines and need to be
`await`ed.

* `close`: close the device
* `open`: open the device
* `update`: get the latest device state (which can then be accessed via the 
`state` property)

# Disclaimer

The code here is based off of an unsupported API from
[Chamberlain](http://www.chamberlain.com/) and is subject to change without
notice. The authors claim no responsibility for damages to your garage door or
property by use of the code within.
