"""Data coordinator for Zodiac Pool Robot."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import ZodiacApiError, ZodiacClient
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ZodiacCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll all supported robots on an iAquaLink account."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: ZodiacClient,
        devices: list[dict[str, Any]],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self.devices = devices

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        data: dict[str, dict[str, Any]] = {}
        for device in self.devices:
            serial = str(device["serial_number"])
            try:
                data[serial] = await self.client.async_get_status(device)
            except ZodiacApiError as err:
                _LOGGER.warning("Unable to update Zodiac robot %s: %s", serial, err)
                previous = (self.data or {}).get(serial, {})
                data[serial] = {
                    **previous,
                    "name": str(device.get("name") or "Zodiac Pool Robot"),
                    "serial_number": serial,
                    "device_type": str(device.get("device_type") or ""),
                    "available": False,
                    "connection": "unavailable",
                }
        return data
