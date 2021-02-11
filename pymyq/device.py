"""Define MyQ devices."""
import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from .const import DEVICE_TYPE, WAIT_TIMEOUT
from .errors import RequestError, MyQError

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)


class MyQDevice:
    """Define a generic device."""

    def __init__(
        self, api: "API", device_json: dict, account: str, state_update: datetime
    ) -> None:
        """Initialize.
        :type account: str
        """
        self._api = api  # type: "API"
        self._account = account  # type: str
        self.device_json = device_json  # type: dict
        self.state_update = state_update  # type: datetime
        self._device_state = None  # Type: Optional[str]

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
        return self._device_state or self.device_state

    @state.setter
    def state(self, value: str) -> None:
        """Set the current state of the device."""
        self._device_state = value

    @property
    def device_state(self) -> Optional[str]:
        return None

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

    async def wait_for_state(
        self,
        current_state: List,
        new_state: List,
        last_state_update: datetime,
        timeout: int = WAIT_TIMEOUT,
    ) -> bool:
        # First wait until door state is actually updated.
        _LOGGER.debug(f"Waiting until device state has been updated for {self.name}")
        wait_timeout = timeout
        while (
            last_state_update
            == self.device_json["state"].get("last_update", datetime.utcnow())
            and wait_timeout > 0
        ):
            wait_timeout = wait_timeout - 5
            await asyncio.sleep(5)
            try:
                await self._api.update_device_info(for_account=self.account)
            except MyQError:
                # Ignoring
                pass

        # Wait until the state is to what we want it to be
        _LOGGER.debug(f"Waiting until device state for {self.name} is {new_state}")
        wait_timeout = timeout
        while self.state in current_state and wait_timeout > 0:
            wait_timeout = wait_timeout - 5
            await asyncio.sleep(5)
            try:
                await self._api.update_device_info(for_account=self.account)
            except MyQError:
                # Ignoring
                pass

        # Reset self.state ensuring it reflects actual device state. Only do this if state is still what it would
        # have been, this to ensure if something else had updated it to something else we don't override.
        if self._device_state == current_state:
            self._device_state = None

        return self.state in new_state
