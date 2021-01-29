"""Define MyQ devices."""
import logging
from asyncio import sleep as asyncio_sleep
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .device import MyQDevice

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

COMMAND_URI = "https://account-devices-gdo.myq-cloud.com/api/v5.2/Accounts/{account_id}/door_openers/{device_serial}/{command}"
COMMAND_CLOSE = "close"
COMMAND_OPEN = "open"
STATE_CLOSED = "closed"
STATE_CLOSING = "closing"
STATE_OPEN = "open"
STATE_OPENING = "opening"
STATE_STOPPED = "stopped"
STATE_TRANSITION = "transition"
STATE_UNKNOWN = "unknown"

WAIT_TIMEOUT = 60


class MyQGaragedoor(MyQDevice):
    """Define a generic device."""

    def __init__(self, api: "API", device_json: dict, account: str, state_update: datetime) -> None:
        """Initialize.
        :type account: str
        """
        super().__init__(api=api, account=account, device_json=device_json, state_update=state_update)

    @property
    def close_allowed(self) -> bool:
        """Return whether the device can be closed unattended."""
        return self.device_json["state"].get("is_unattended_close_allowed") is True

    @property
    def open_allowed(self) -> bool:
        """Return whether the device can be opened unattended."""
        return self.device_json["state"].get("is_unattended_open_allowed") is True

    @property
    def state(self) -> Optional[str]:
        """Return the current state of the device."""
        return (
            self.device_json["state"].get("door_state")
            if self.device_json.get("state") is not None
            else None
        )

    @state.setter
    def state(self, value: str) -> None:
        """Set the current state of the device."""
        if self.device_json.get("state") is None:
            return
        self.device_json["state"]["door_state"] = value

    async def close(self, wait_for_state: bool = False) -> bool:
        """Close the device."""
        if self.state not in (STATE_CLOSED, STATE_CLOSING):
            # Set the current state to "closing" right away (in case the user doesn't
            # run update() before checking):
            self.state = STATE_CLOSING
            await self._send_state_command(
                url=COMMAND_URI.format(
                    account_id=self.account,
                    device_serial=self.device_id,
                    command=COMMAND_CLOSE,
                ),
                command=COMMAND_CLOSE,
            )

        if not wait_for_state:
            return True

        # First wait until door state is actually updated.
        last_update = self.device_json["state"]["last_update"]
        wait_timeout = WAIT_TIMEOUT
        while (
            last_update == self.device_json["state"]["last_update"] and wait_timeout > 0
        ):
            wait_timeout = wait_timeout - 5
            await asyncio_sleep(5)
            await self.update()

        # Wait until the state is not closing anymore.
        wait_timeout = WAIT_TIMEOUT
        while self.state == STATE_CLOSING and wait_timeout > 0:
            wait_timeout = wait_timeout - 5
            await asyncio_sleep(5)
            await self.update()

        return self.state == STATE_CLOSED

    async def open(self, wait_for_state: bool = False) -> bool:
        """Open the device."""
        if self.state not in (STATE_OPEN, STATE_OPENING):
            # Set the current state to "opening" right away (in case the user doesn't
            # run update() before checking):
            self.state = STATE_OPENING
            await self._send_state_command(
                url=COMMAND_URI.format(
                    account_id=self.account,
                    device_serial=self.device_id,
                    command=COMMAND_OPEN,
                ),
                command=COMMAND_OPEN,
            )

        if not wait_for_state:
            return True

        # First wait until door state is actually updated.
        last_update = self.device_json["state"]["last_update"]
        wait_timeout = WAIT_TIMEOUT
        while (
            last_update == self.device_json["state"]["last_update"] and wait_timeout > 0
        ):
            wait_timeout = wait_timeout - 5
            await asyncio_sleep(5)
            await self.update()

        # Wait until the state is not open anymore.
        wait_timeout = WAIT_TIMEOUT
        while self.state == STATE_OPENING and wait_timeout > 0:
            wait_timeout = wait_timeout - 5
            await asyncio_sleep(5)
            await self.update()

        return self.state == STATE_OPEN
