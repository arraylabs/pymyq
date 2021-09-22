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
    "https://account-devices-lock.myq-cloud.com/api/v5.2/Accounts/{account_id}"
    "/locks/{device_serial}/{command}"
)


class MyQLock(MyQDevice):
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
            self.device_json["state"].get("lock_state")
            if self.device_json.get("state") is not None
            else None
        )

