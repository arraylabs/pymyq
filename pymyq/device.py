"""Define MyQ devices."""
import logging
import re
from typing import TYPE_CHECKING, Optional

from .errors import RequestError

from .const import DEVICE_TYPE, DEVICES_API_VERSION

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

COMMAND_CLOSE = "close"
COMMAND_OPEN = "open"

STATE_CLOSED = "closed"
STATE_CLOSING = "closing"
STATE_OPEN = "open"
STATE_OPENING = "opening"
STATE_STOPPED = "stopped"
STATE_TRANSITION = "transition"
STATE_UNKNOWN = "unknown"


class MyQDevice:
    """Define a generic device."""

    def __init__(self, api: "API", device_json: dict):
        """Initialize."""
        self._api = api
        self.device_json = device_json

    @property
    def close_allowed(self) -> bool:
        """Return whether the device can be closed unattended."""
        return self.device_json["state"].get("is_unattended_close_allowed") is True

    @property
    def device_family(self) -> str:
        """Return the family in which this device lives."""
        return self.device_json["device_family"]

    @property
    def device_id(self) -> str:
        """Return the device ID (serial number)."""
        return self.device_json["serial_number"]

    @property
    def device_platform(self) -> str:
        """Return the device platform."""
        return self.device_json["device_platform"]

    @property
    def device_type(self) -> str:
        """Return the device type."""
        return self.device_json[DEVICE_TYPE]

    @property
    def firmware_version(self) -> Optional[str]:
        """Return the family in which this device lives."""
        return self.device_json["state"].get("firmware_version")

    @property
    def name(self) -> bool:
        """Return the device name."""
        return self.device_json["name"]

    @property
    def online(self) -> bool:
        """Return whether the device is online."""
        return self.device_json["state"].get("online") is True

    @property
    def open_allowed(self) -> bool:
        """Return whether the device can be opened unattended."""
        return self.device_json["state"].get("is_unattended_open_allowed") is True

    @property
    def parent_device_id(self) -> Optional[str]:
        """Return the device ID (serial number) of this device's parent."""
        return self.device_json.get("parent_device_id")

    @property
    def state(self) -> Optional[str]:
        """Return the current state of the device."""
        return self.device_json["state"].get("door_state")

    @property
    def href(self) -> Optional[str]:
        """Return the hyperlinks of the device."""
        return self.device_json.get("href")

    @state.setter
    def state(self, value: str) -> None:
        """Set the current state of the device."""
        if not self.device_json["state"].get("door_state"):
            return
        self.device_json["state"]["door_state"] = value

    async def _send_state_command(self, state_command: str) -> None:
        """Instruct the API to change the state of the device."""
        # If the user tries to open or close, say, a gateway, throw an exception:
        if not self.state:
            raise RequestError(
                "Cannot change state of device type: {0}".format(self.device_type)
            )

        account_id = self._api.account_id
        if self.href is not None:
            rule = r".*/accounts/(.*)/devices/(.*)"
            infos = re.search(rule, self.href)
            if infos is not None:
                account_id = infos.group(1)
        _LOGGER.debug(f"Sending command {state_command} for {self.name}")
        await self._api.request(
            method="put",
            endpoint="Accounts/{0}/Devices/{1}/actions".format(
                account_id, self.device_id
            ),
            json={"action_type": state_command},
            api_version=DEVICES_API_VERSION
        )

    async def close(self) -> None:
        """Close the device."""
        if self.state in (STATE_CLOSED, STATE_CLOSING):
            return

        # Set the current state to "closing" right away (in case the user doesn't
        # run update() before checking):
        self.state = STATE_CLOSING
        await self._send_state_command(COMMAND_CLOSE)

    async def open(self) -> None:
        """Open the device."""
        if self.state in (STATE_OPEN, STATE_OPENING):
            return

        # Set the current state to "opening" right away (in case the user doesn't
        # run update() before checking):
        self.state = STATE_OPENING
        await self._send_state_command(COMMAND_OPEN)

    async def update(self) -> None:
        """Get the latest info for this device."""
        await self._api.update_device_info()
