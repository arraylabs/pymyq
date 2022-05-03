"""Define MyQ accounts."""

import asyncio
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Dict, Optional

from .const import (
    DEVICE_FAMILY_GARAGEDOOR,
    DEVICE_FAMILY_GATEWAY,
    DEVICE_FAMILY_LAMP,
    DEVICE_FAMILY_LOCK,
    DEVICES_ENDPOINT,
)
from .device import MyQDevice
from .errors import MyQError
from .garagedoor import MyQGaragedoor
from .lamp import MyQLamp
from .lock import MyQLock

if TYPE_CHECKING:
    from .api import API

_LOGGER = logging.getLogger(__name__)

DEFAULT_STATE_UPDATE_INTERVAL = timedelta(seconds=5)


class MyQAccount:
    """Define an account."""

    def __init__(self, api: "API", account_json: dict, devices: Optional[dict] = None) -> None:

        self._api = api
        self.account_json = account_json
        if devices is None:
            devices = {}
        self._devices = devices
        self.last_state_update = None  # type: Optional[datetime]
        self._update = asyncio.Lock()  # type: asyncio.Lock

    @property
    def api(self) -> "API":
        """Return API object"""
        return self._api

    @property
    def id(self) -> Optional[str]:
        """Return account id """
        return self.account_json.get("id")

    @property
    def name(self) -> Optional[str]:
        """Return account name"""
        return self.account_json.get("name")

    @property
    def devices(self) -> Dict[str, MyQDevice]:
        """Return all devices within account"""
        return self._devices

    @property
    def covers(self) -> Dict[str, MyQGaragedoor]:
        """Return only those devices that are covers."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if isinstance(device, MyQGaragedoor)
        }

    @property
    def lamps(self) -> Dict[str, MyQLamp]:
        """Return only those devices that are lamps."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if isinstance(device, MyQLamp)
        }

    @property
    def gateways(self) -> Dict[str, MyQDevice]:
        """Return only those devices that are gateways."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if device.device_json["device_family"] == DEVICE_FAMILY_GATEWAY
        }

    @property
    def locks(self) -> Dict[str, MyQDevice]:
        """Return only those devices that are locks."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if device.device_json["device_family"] == DEVICE_FAMILY_LOCK
        }

    @property
    def other(self) -> Dict[str, MyQDevice]:
        """Return only those devices that are others."""
        return {
            device_id: device
            for device_id, device in self.devices.items()
            if type(device) is MyQDevice
            and device.device_json["device_family"] != DEVICE_FAMILY_GATEWAY
        }

    async def _get_devices(self) -> None:

        _LOGGER.debug("Retrieving devices for account %s", self.name or self.id)

        _, devices_resp = await self._api.request(
            method="get",
            returns="json",
            url=DEVICES_ENDPOINT.format(account_id=self.id),
        )

        if devices_resp is not None and not isinstance(devices_resp, dict):
            raise MyQError(
                f"Received object devices_resp of type {type(devices_resp)} but expecting type dict"
            )

        state_update_timestmp = datetime.utcnow()
        if devices_resp is not None and devices_resp.get("items") is not None:
            for device in devices_resp.get("items"):
                serial_number = device.get("serial_number")
                if serial_number is None:
                    _LOGGER.debug(
                        "No serial number for device with name %s.", device.get("name")
                    )
                    continue

                if serial_number in self._devices:
                    _LOGGER.debug(
                        "Updating information for device with serial number %s",
                        serial_number,
                    )
                    myqdevice = self._devices[serial_number]
                    myqdevice.device_json = device
                    myqdevice.last_state_update = state_update_timestmp

                else:
                    if device.get("device_family") == DEVICE_FAMILY_GARAGEDOOR:
                        _LOGGER.debug(
                            "Adding new garage door with serial number %s",
                            serial_number,
                        )
                        new_device = MyQGaragedoor(
                            account=self,
                            device_json=device,
                            state_update=state_update_timestmp,
                        )
                    elif device.get("device_family") == DEVICE_FAMILY_LAMP:
                        _LOGGER.debug(
                            "Adding new lamp with serial number %s", serial_number
                        )
                        new_device = MyQLamp(
                            account=self,
                            device_json=device,
                            state_update=state_update_timestmp,
                        )
                    elif device.get("device_family") == DEVICE_FAMILY_LOCK:
                        _LOGGER.debug(
                            "Adding new lock with serial number %s", serial_number
                        )
                        new_device = MyQLock(
                            account=self,
                            device_json=device,
                            state_update=state_update_timestmp,
                        )
                    else:
                        if device.get("device_family") == DEVICE_FAMILY_GATEWAY:
                            _LOGGER.debug(
                                "Adding new gateway with serial number %s",
                                serial_number,
                            )
                        else:
                            _LOGGER.debug(
                                "Adding unknown device family %s with serial number %s",
                                device.get("device_family"),
                                serial_number,
                            )

                        new_device = MyQDevice(
                            account=self,
                            device_json=device,
                            state_update=state_update_timestmp,
                        )

                    if new_device:
                        self._devices[serial_number] = new_device
        else:
            _LOGGER.debug("No devices found for account %s", self.name or self.id)

    async def update(self) -> None:
        """Get up-to-date device info."""
        # The MyQ API can time out if state updates are too frequent; therefore,
        # if back-to-back requests occur within a threshold, respond to only the first
        # Ensure only 1 update task can run at a time.
        async with self._update:
            call_dt = datetime.utcnow()
            if not self.last_state_update:
                self.last_state_update = call_dt - DEFAULT_STATE_UPDATE_INTERVAL
            next_available_call_dt = (
                self.last_state_update + DEFAULT_STATE_UPDATE_INTERVAL
            )

            # Ensure we're within our minimum update interval
            if call_dt < next_available_call_dt:
                _LOGGER.debug(
                    "Ignoring device update request for account %s as it is within throttle window",
                    self.name or self.id,
                )
                return

            await self._get_devices()
            self.last_state_update = datetime.utcnow()
