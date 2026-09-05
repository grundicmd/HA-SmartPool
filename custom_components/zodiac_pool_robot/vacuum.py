"""Vacuum entity for Zodiac Pool Robot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ZodiacConfigEntry
from .api import ZodiacApiError
from .entity import ZodiacEntity


async def async_setup_entry(
    hass: Any,
    entry: ZodiacConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Zodiac vacuum entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ZodiacPoolVacuum(coordinator, str(device["serial_number"]))
        for device in coordinator.devices
    )


class ZodiacPoolVacuum(ZodiacEntity, StateVacuumEntity):
    """Pool-cleaner representation of a Zodiac robot."""

    _attr_name = None
    _attr_supported_features = VacuumEntityFeature.START | VacuumEntityFeature.STOP

    def __init__(self, coordinator: Any, serial: str) -> None:
        super().__init__(coordinator, serial, "vacuum")

    @property
    def activity(self) -> VacuumActivity:
        """Return current vacuum activity."""
        if self.robot_data.get("error_code"):
            return VacuumActivity.ERROR
        if self.robot_data.get("running"):
            return VacuumActivity.CLEANING
        return VacuumActivity.IDLE

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return useful robot diagnostics."""
        data = self.robot_data
        return {
            "connection": data.get("connection"),
            "cleaning_cycle": data.get("cleaning_cycle"),
            "canister": data.get("canister"),
            "remaining_minutes": data.get("remaining_minutes"),
            "total_runtime_hours": data.get("total_runtime_hours"),
            "error_code": data.get("error_code"),
            "error": data.get("error"),
            "control_box_firmware": data.get("control_box_firmware"),
            "robot_firmware": data.get("robot_firmware"),
        }

    async def async_start(self) -> None:
        """Start cleaning."""
        await self._async_set_running(True)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        await self._async_set_running(False)

    async def _async_set_running(self, running: bool) -> None:
        device = next(
            device
            for device in self.coordinator.devices
            if str(device["serial_number"]) == self.serial
        )
        try:
            await self.coordinator.client.async_set_running(device, running)
        except ZodiacApiError:
            await self.coordinator.async_request_refresh()
            raise
        await self.coordinator.async_request_refresh()
