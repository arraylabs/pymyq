# Introduction

This is a python module aiming to interact with the Chamberlain MyQ API.

Code is licensed under the MIT license.

Getting Started
===============

# Usage

```python
from pymyq import MyQAPI as pymyq

myq = pymyq(username, password, brand)
```

# Methods

def is_supported_brand(self):
"""Return true/false based on supported brands list and input."""

def is_login_valid(self):
"""Return true/false based on successful authentication."""

def get_devices(self):
"""Return devices from API"""

def get_garage_doors(self):
"""Parse devices data and extract garage doors. Return garage doors."""
       
def get_status(self, device_id):
"""Return current door status(open/closed)"""

def close_device(self, device_id):
"""Send request to close the door."""

def open_device(self, device_id):
"""Send request to open the door."""

def set_state(self, device_id, state):
"""Send request for request door state change."""

### Disclaimer

The code here is based off of an unsupported API from [Chamberlain](http://www.chamberlain.com/) and is subject to change without notice. The authors claim no responsibility for damages to your garage door or property by use of the code within.
