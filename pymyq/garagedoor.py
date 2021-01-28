"""Define MyQ devices."""
import logging
from typing import TYPE_CHECKING, Optional

from .device import MyQDevice

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

COMMAND_URI = \
    "https://account-devices-gdo.myq-cloud.com/api/v5.2/Accounts/{account_id}/door_openers/{device_serial}/{command}"
COMMAND_CLOSE = "close"
COMMAND_OPEN = "open"
STATE_CLOSED = "closed"
STATE_CLOSING = "closing"
STATE_OPEN = "open"
STATE_OPENING = "opening"
STATE_STOPPED = "stopped"
STATE_TRANSITION = "transition"
STATE_UNKNOWN = "unknown"


class MyQGaragedoor(MyQDevice):
    """Define a generic device."""

    def __init__(self, api: "API", device_json: dict, account: str) -> None:
        """Initialize.
        :type account: str
        """
        super().__init__(api=api, account=account, device_json=device_json)

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

    async def close(self) -> None:
        """Close the device."""
        if self.state in (STATE_CLOSED, STATE_CLOSING):
            return

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

    async def open(self) -> None:
        """Open the device."""
        if self.state in (STATE_OPEN, STATE_OPENING):
            return

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
