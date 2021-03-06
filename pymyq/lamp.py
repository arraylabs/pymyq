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
    "https://account-devices-lamp.myq-cloud.com/api/v5.2/Accounts/{account_id}"
    "/lamps/{device_serial}/{command}"
)
COMMAND_ON = "on"
COMMAND_OFF = "off"
STATE_ON = "on"
STATE_OFF = "off"


class MyQLamp(MyQDevice):
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
    def device_state(self) -> Optional[str]:
        """Return the current state of the device."""
        return (
            self.device_json["state"].get("lamp_state")
            if self.device_json.get("state") is not None
            else None
        )

    async def turnoff(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Turn light off."""

        return await self._send_state_command(
            to_state=STATE_OFF,
            intermediate_state=STATE_OFF,
            url=COMMAND_URI.format(
                account_id=self.account.id,
                device_serial=self.device_id,
                command=COMMAND_OFF,
            ),
            command=COMMAND_OFF,
            wait_for_state=wait_for_state,
        )

    async def turnon(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Turn light on."""

        return await self._send_state_command(
            to_state=STATE_ON,
            intermediate_state=STATE_ON,
            url=COMMAND_URI.format(
                account_id=self.account.id,
                device_serial=self.device_id,
                command=COMMAND_ON,
            ),
            command=COMMAND_ON,
            wait_for_state=wait_for_state,
        )
