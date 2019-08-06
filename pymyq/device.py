"""Define MyQ devices."""
import logging
from typing import TYPE_CHECKING

from .errors import RequestError

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

STATE_OPEN = "open"
STATE_CLOSED = "closed"
STATE_STOPPED = "stopped"
STATE_OPENING = "opening"
STATE_CLOSING = "closing"
STATE_UNKNOWN = "unknown"
STATE_TRANSITION = "transition"


class Device:
    """Define a generic device."""

    def __init__(self, api: "API", device_json: dict):
        """Initialize."""
        self._api = api
        self.device_json = device_json

    @property
    def close_allowed(self) -> bool:
        """Return whether the device can be closed unattended."""
        return self.device_json["state"].get("is_unattended_close_allowed")

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
        return self.device_json["device_type"]

    @property
    def firmware_version(self) -> str:
        """Return the family in which this device lives."""
        return self.device_json["state"].get("firmware_version")

    @property
    def name(self) -> bool:
        """Return the device name."""
        return self.device_json["name"]

    @property
    def online(self) -> bool:
        """Return whether the device is online."""
        return self.device_json["online"]

    @property
    def open_allowed(self) -> bool:
        """Return whether the device can be opened unattended."""
        return self.device_json["state"].get("is_unattended_open_allowed")

    @property
    def parent_device_id(self) -> str:
        """Return the device ID (serial number) of this device's parent."""
        return self.device_json.get("parent_device_id")

    @property
    def state(self) -> str:
        """Return the current state of the device."""
        return self.device_json["state"].get("door_state")

    async def _send_state_command(self, state: str) -> None:
        """Instruct the API to change the state of the device."""
        if not self.device_json["state"].get("door_state"):
            raise RequestError(
                "Cannot change state of device type: {0}".format(self.device_type)
            )

        await self._api.request(
            "put",
            endpoint="Accounts/{0}/Devices/{1}/actions".format(
                self._api.account_id, self.device_id
            ),
            json={"action_type": state},
        )

    async def close(self) -> None:
        """Close the device."""
        if self.device_json["state"]["door_state"] in (STATE_CLOSED, STATE_CLOSING):
            return

        # Set the current state to "closing" right away (in case the user doesn't
        # run update() before checking):
        self.device_json["state"]["door_state"] = STATE_CLOSING
        await self._send_state_command("close")

    async def open(self) -> None:
        """Open the device."""
        if self.device_json["state"]["door_state"] in (STATE_OPEN, STATE_OPENING):
            return

        # Set the current state to "opening" right away (in case the user doesn't
        # run update() before checking):
        self.device_json["state"]["door_state"] = STATE_OPENING
        await self._send_state_command("open")

    async def update(self) -> None:
        """Get the latest info for this device."""
        await self._api.update_device_info()
