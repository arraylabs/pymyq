"""Define MyQ devices."""
import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

from .device import MyQDevice

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

COMMAND_URI = "https://account-devices-lamp.myq-cloud.com/api/v5.2/Accounts/{account_id}/lamps/{device_serial}/{command}"
COMMAND_ON = "on"
COMMAND_OFF = "off"
STATE_ON = "on"
STATE_OFF = "off"


class MyQLamp(MyQDevice):
    """Define a generic device."""

    def __init__(
        self, api: "API", device_json: dict, account: str, state_update: datetime
    ) -> None:
        """Initialize.
        :type account: str
        """
        super().__init__(
            api=api, account=account, device_json=device_json, state_update=state_update
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

        await self._send_state_command(
            url=COMMAND_URI.format(
                account_id=self.account,
                device_serial=self.device_id,
                command=COMMAND_OFF,
            ),
            command=COMMAND_OFF,
        )
        self.state = STATE_OFF

        wait_for_state_task = asyncio.create_task(
            self.wait_for_state(
                current_state=[STATE_ON],
                new_state=[STATE_OFF],
                last_state_update=self.device_json["state"].get("last_update"),
                timeout=30,
            ),
            name="MyQ_WaitForOff",
        )
        if not wait_for_state:
            return wait_for_state_task

        _LOGGER.debug("Waiting till light is off")
        return await wait_for_state_task

    async def turnon(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Turn light on."""

        await self._send_state_command(
            url=COMMAND_URI.format(
                account_id=self.account,
                device_serial=self.device_id,
                command=COMMAND_ON,
            ),
            command=COMMAND_ON,
        )
        self.state = STATE_ON

        wait_for_state_task = asyncio.create_task(
            self.wait_for_state(
                current_state=[STATE_ON],
                new_state=[STATE_OFF],
                last_state_update=self.device_json["state"].get("last_update"),
                timeout=30,
            ),
            name="MyQ_WaitForOn",
        )
        if not wait_for_state:
            return wait_for_state_task

        _LOGGER.debug("Waiting till light is on")
        return await wait_for_state_task