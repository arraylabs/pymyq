"""Define MyQ devices."""
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from .device import MyQDevice

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

COMMAND_URI = \
    "https://account-devices-lamp.myq-cloud.com/api/v5.2/Accounts/{account_id}/lamps/{device_serial}/{command}"
COMMAND_ON = "on"
COMMAND_OFF = "off"
STATE_ON = "on"
STATE_OFF = "off"


class MyQLamp(MyQDevice):
    """Define a generic device."""

    def __init__(self, api: "API", device_json: dict, account: str, state_update: datetime) -> None:
        """Initialize.
        :type account: str
        """
        super().__init__(api=api, account=account, device_json=device_json, state_update=state_update)

    @property
    def device_state(self) -> Optional[str]:
        """Return the current state of the device."""
        return (
            self.device_json["state"].get("lamp_state")
            if self.device_json.get("state") is not None
            else None
        )

    async def turnoff(self) -> None:
        """Close the device."""
        if self.state == STATE_OFF:
            return

        # Set the current state to "closing" right away (in case the user doesn't
        # run update() before checking):
        self.state = STATE_OFF
        await self._send_state_command(
            url=COMMAND_URI.format(
                account_id=self.account,
                device_serial=self.device_id,
                command=COMMAND_OFF,
            ),
            command=COMMAND_OFF,
        )

    async def turnon(self) -> None:
        """Open the device."""
        if self.state == STATE_ON:
            return

        # Set the current state to "opening" right away (in case the user doesn't
        # run update() before checking):
        self.state = STATE_ON
        await self._send_state_command(
            url=COMMAND_URI.format(
                account_id=self.account,
                device_serial=self.device_id,
                command=COMMAND_ON,
            ),
            command=COMMAND_ON,
        )
