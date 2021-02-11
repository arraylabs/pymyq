"""Define MyQ devices."""
import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

from .device import MyQDevice
from .errors import RequestError

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
    def device_state(self) -> Optional[str]:
        """Return the current state of the device."""
        return (
            self.device_json["state"].get("door_state")
            if self.device_json.get("state") is not None
            else None
        )

    async def close(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Close the device."""
        if self.state != self.device_state:
            raise RequestError(f"Device is currently {self.state}, wait until complete.")

        if self.state not in (STATE_CLOSED, STATE_CLOSING):
            # If our state is different from device state then it means an action is already being performed.
            if self.state != self.device_state:
                raise RequestError(f"Device is currently {self.state}, wait until complete.")

            # Device is currently not closed or closing, send command to close
            await self._send_state_command(
                url=COMMAND_URI.format(
                    account_id=self.account,
                    device_serial=self.device_id,
                    command=COMMAND_CLOSE,
                ),
                command=COMMAND_CLOSE,
            )
            self.state = STATE_CLOSING

        wait_for_state_task = asyncio.create_task(self.wait_for_state(
            current_state=[STATE_CLOSING],
            new_state=[STATE_CLOSED],
            last_state_update=self.device_json["state"].get("last_update"),
            timeout=60,
        ), name="MyQ_WaitForClose",
        )
        if not wait_for_state:
            return wait_for_state_task

        _LOGGER.debug("Waiting till garage is closed")
        return await wait_for_state_task

    async def open(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        """Open the device."""
        if self.state not in (STATE_OPEN, STATE_OPENING):
            # Set the current state to "opening" right away (in case the user doesn't
            # run update() before checking):
            await self._send_state_command(
                url=COMMAND_URI.format(
                    account_id=self.account,
                    device_serial=self.device_id,
                    command=COMMAND_OPEN,
                ),
                command=COMMAND_OPEN,
            )
            self.state = STATE_OPENING

        wait_for_state_task = asyncio.create_task(self.wait_for_state(
            current_state=[STATE_OPENING],
            new_state=[STATE_OPEN],
            last_state_update=self.device_json["state"].get("last_update"),
            timeout=60,
        ), name="MyQ_WaitForOpen",
        )

        if not wait_for_state:
            return wait_for_state_task

        _LOGGER.debug("Waiting till garage is open")
        return await wait_for_state_task
