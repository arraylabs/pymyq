"""Define MyQ devices."""
import logging
from typing import TYPE_CHECKING, Optional

from .const import DEVICE_TYPE
from .errors import RequestError

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)


class MyQDevice:
    """Define a generic device."""

    def __init__(self, api: "API", device_json: dict, account: str, state_update: datetime) -> None:
        """Initialize.
        :type account: str
        """
        self._api = api
        self._account = account
        self.device_json = device_json
        self.state_update = state_update

    @property
    def account(self) -> str:
        """Return account associated with device"""
        return self._account

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
    def parent_device_id(self) -> Optional[str]:
        """Return the device ID (serial number) of this device's parent."""
        return self.device_json.get("parent_device_id")

    @property
    def href(self) -> Optional[str]:
        """Return the hyperlinks of the device."""
        return self.device_json.get("href")

    @property
    def state(self) -> Optional[str]:
        return None

    @state.setter
    def state(self, value: str) -> None:
        return

    @property
    def close_allowed(self) -> bool:
        """Return whether the device can be closed unattended."""
        return False

    @property
    def open_allowed(self) -> bool:
        """Return whether the device can be opened unattended."""
        return False

    async def _send_state_command(self, url: str, command: str) -> None:
        """Instruct the API to change the state of the device."""
        # If the user tries to open or close, say, a gateway, throw an exception:
        if not self.state:
            raise RequestError(
                f"Cannot change state of device type: {self.device_type}"
            )

        _LOGGER.debug(f"Sending command {command} for {self.name}")
        await self._api.request(
            method="put",
            returns="response",
            url=url,
        )

    async def update(self) -> None:
        """Get the latest info for this device."""
        await self._api.update_device_info()
