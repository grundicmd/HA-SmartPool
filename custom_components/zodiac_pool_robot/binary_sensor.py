"""Binary sensors for Zodiac Pool Robot."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ZodiacConfigEntry
from .entity import ZodiacEntity


async def async_setup_entry(
    hass: Any,
    entry: ZodiacConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Zodiac connectivity sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ZodiacConnectivity(coordinator, str(device["serial_number"]))
        for device in coordinator.devices
    )


class ZodiacConnectivity(ZodiacEntity, BinarySensorEntity):
    """Robot cloud connectivity sensor."""

    _attr_translation_key = "connectivity"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: Any, serial: str) -> None:
        super().__init__(coordinator, serial, "connectivity")

    @property
    def is_on(self) -> bool:
        """Return whether the robot reports cloud connectivity."""
        return bool(self.robot_data.get("available"))
