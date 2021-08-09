"""Define MyQ devices."""
import asyncio
from datetime import datetime
import logging
from typing import TYPE_CHECKING, Optional, Union

from .device import MyQDevice

if TYPE_CHECKING:
    from .account import MyQAccount

_LOGGER = logging.getLogger(__name__)

COMMAND_URI = (
    "https://account-devices-gdo.myq-cloud.com/api/v5.2/Accounts/{account_id}"
    "/door_openers/{device_serial}/{command}"
)
COMMAND_CLOSE = "close"
COMMAND_OPEN = "open"
STATE_CLOSED = "closed"
STATE_CLOSING = "closing"
STATE_OPEN = "open"
STATE_OPENING = "opening"
STATE_STOPPED = "stopped"
STATE_UNKNOWN = "unknown"


class MyQGaragedoor(MyQDevice):
    """Define a generic device."""

    def __init__(
        self,
        device_json: dict,
        account: "MyQAccount",
        state_update: datetime,
    ) -> None:
        """Initialize.
        :type account: str
        """
        super().__init__(
            account=account, device_json=device_json, state_update=state_update
        )

    @property
    def close_allowed(self) -> bool:
        """Return whether the device can be closed unattended."""
        return self.device_json["state"].get("is_unattended_close_allowed") is True

    @property
    def open_allowed(self) -> bool:
        """Return whether the device can be opened unattended."""
        return self.device_json["state"].get("is_unattended_open_allowed") is True

    @property
    def device_state(self) -> Optional[str]:
        """Return the current state of the device."""
        return (
            self.device_json["state"].get("door_state")
            if self.device_json.get("state") is not None
            else None
        )

    async def close(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Close the device."""

        return await self._send_state_command(
            to_state=STATE_CLOSED,
            intermediate_state=STATE_CLOSING,
            url=COMMAND_URI.format(
                account_id=self.account.id,
                device_serial=self.device_id,
                command=COMMAND_CLOSE,
            ),
            command=COMMAND_CLOSE,
            wait_for_state=wait_for_state,
        )

    async def open(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Open the device."""

        return await self._send_state_command(
            to_state=STATE_OPEN,
            intermediate_state=STATE_OPENING,
            url=COMMAND_URI.format(
                account_id=self.account.id,
                device_serial=self.device_id,
                command=COMMAND_OPEN,
            ),
            command=COMMAND_OPEN,
            wait_for_state=wait_for_state,
        )
