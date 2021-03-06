"""Define MyQ devices."""
import asyncio
from datetime import datetime
import logging
from typing import TYPE_CHECKING, List, Optional, Union

from .const import DEVICE_TYPE, WAIT_TIMEOUT
from .errors import MyQError, RequestError

if TYPE_CHECKING:
    from .account import MyQAccount

_LOGGER = logging.getLogger(__name__)


class MyQDevice:
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
        self._account = account
        self.device_json = device_json
        self.last_state_update = state_update
        self.state_update = None
        self._device_state = None  # Type: Optional[str]
        self._send_command_lock = asyncio.Lock()  # type: asyncio.Lock
        self._wait_for_state_task = None

    @property
    def account(self) -> "MyQAccount":
        """Return account associated with device"""
        return self._account

    @property
    def device_family(self) -> Optional[str]:
        """Return the family in which this device lives."""
        return self.device_json.get("device_family")

    @property
    def device_id(self) -> Optional[str]:
        """Return the device ID (serial number)."""
        return self.device_json.get("serial_number")

    @property
    def device_platform(self) -> Optional[str]:
        """Return the device platform."""
        return self.device_json.get("device_platform")

    @property
    def device_type(self) -> Optional[str]:
        """Return the device type."""
        return self.device_json.get(DEVICE_TYPE)

    @property
    def firmware_version(self) -> Optional[str]:
        """Return the family in which this device lives."""
        return self.device_json["state"].get("firmware_version")

    @property
    def name(self) -> Optional[str]:
        """Return the device name."""
        return self.device_json.get("name")

    @property
    def online(self) -> bool:
        """Return whether the device is online."""
        state = self.device_json.get("state")
        if state is None:
            return False

        return state.get("online") is True

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
        """Return current state

        Returns:
            Optional[str]: State for the device
        """
        return self._device_state or self.device_state

    @state.setter
    def state(self, value: str):
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

    async def close(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        raise NotImplementedError

    async def open(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        raise NotImplementedError

    async def turnoff(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        raise NotImplementedError

    async def turnon(self, wait_for_state: bool = False) -> Union[asyncio.Task, bool]:
        raise NotImplementedError

    async def update_device(self, device_json: dict, state_update_timestmp: datetime):
        """Update state of device depending on last update in MyQ is after last state set

        by us

        Args:
            device_json (dict): device json
            state_update_timestmp (datetime): [description]
        """
        # When performing commands we might update the state temporary, need to ensure
        # that the state is not set back to something else if MyQ does not yet have updated
        # state
        last_update = self.device_json["state"].get("last_update")
        self.device_json = device_json

        if (
            self.device_json["state"].get("last_update") is not None
            and self.device_json["state"].get("last_update") != last_update
        ):
            # MyQ has updated device state, reset ours ensuring we have the one from MyQ.
            self._device_state = None
            _LOGGER.debug(
                "State for device %s was updated to %s", self.name, self.state
            )

        self.state_update = state_update_timestmp

    async def _send_state_command(
        self,
        to_state: str,
        intermediate_state: str,
        url: str,
        command: str,
        wait_for_state: bool = False,
    ) -> Union[asyncio.Task, bool]:
        """Send command to device to change state."""

        # If the user tries to open or close, say, a gateway, throw an exception:
        if not self.state:
            raise RequestError(
                f"Cannot change state of device type: {self.device_type}"
            )

        # If currently there is a wait_for_state task running,
        # then wait until it completes first.
        if self._wait_for_state_task is not None:
            # Return wait task if we're currently waiting for same task to be completed
            if self.state == intermediate_state and not wait_for_state:
                _LOGGER.debug(
                    "Command %s for %s was already send, returning wait task for it instead",
                    command,
                    self.name,
                )
                return self._wait_for_state_task

            _LOGGER.debug(
                "Another command for %s is still in progress, waiting for it to complete first before issuing command %s",
                self.name,
                command,
            )
            await self._wait_for_state_task

        # We return true if state is already closed.
        if self.state == to_state:
            _LOGGER.debug(
                "Device %s is in state %s, nothing to do.", self.name, to_state
            )
            return True

        async with self._send_command_lock:
            _LOGGER.debug("Sending command %s for %s", command, self.name)
            await self.account.api.request(
                method="put",
                returns="response",
                url=url,
            )

            self.state = intermediate_state

            self._wait_for_state_task = asyncio.create_task(
                self.wait_for_state(
                    current_state=[self.state],
                    new_state=[to_state],
                    last_state_update=self.device_json["state"].get("last_update"),
                    timeout=60,
                ),
                name="MyQ_WaitFor" + to_state,
            )

            # Make sure our wait task starts
            await asyncio.sleep(0)

        if not wait_for_state:
            return self._wait_for_state_task

        _LOGGER.debug("Waiting till device is %s", to_state)
        return await self._wait_for_state_task

    async def update(self) -> None:
        """Get the latest info for this device."""
        await self.account.update()

    async def wait_for_state(
        self,
        current_state: List,
        new_state: List,
        last_state_update: datetime,
        timeout: int = WAIT_TIMEOUT,
    ) -> bool:
        """Wait until device has reached new state

        Args:
            current_state (List): List of possible current states
            new_state (List): List of new states to wait for
            last_state_update (datetime): Last time state was updated
            timeout (int, optional): Timeout in seconds to wait for new state.
                                     Defaults to WAIT_TIMEOUT.

        Returns:
            bool: True if new state reached, False if new state was not reached
        """
        # First wait until door state is actually updated.
        _LOGGER.debug("Waiting until device state has been updated for %s", self.name)
        wait_timeout = timeout
        while (
            last_state_update
            == self.device_json["state"].get("last_update", datetime.utcnow())
            and wait_timeout > 0
        ):
            wait_timeout = wait_timeout - 5
            try:
                await self._account.update()
            except MyQError:
                # Ignoring
                pass
            await asyncio.sleep(5)

        # Wait until the state is to what we want it to be
        _LOGGER.debug("Waiting until device state for %s is %s", self.name, new_state)
        wait_timeout = timeout
        while self.device_state not in new_state and wait_timeout > 0:
            wait_timeout = wait_timeout - 5
            try:
                await self._account.update()
            except MyQError:
                # Ignoring
                pass
            await asyncio.sleep(5)

        # Reset self.state ensuring it reflects actual device state.
        # Only do this if state is still what it would have been,
        # this to ensure if something else had updated it to something else we don't override.
        if self._device_state in current_state or self._device_state in new_state:
            self._device_state = None

        self._wait_for_state_task = None
        return self.state in new_state
