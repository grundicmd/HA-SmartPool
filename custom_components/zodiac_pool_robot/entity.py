"""Base entity for Zodiac Pool Robot."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZodiacCoordinator


class ZodiacEntity(CoordinatorEntity[ZodiacCoordinator]):
    """Base Zodiac robot entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ZodiacCoordinator, serial: str, key: str) -> None:
        super().__init__(coordinator)
        self.serial = serial
        self._attr_unique_id = f"{serial}_{key}"

    @property
    def robot_data(self) -> dict[str, Any]:
        """Return current normalized robot data."""
        return self.coordinator.data.get(self.serial, {})

    @property
    def available(self) -> bool:
        """Return whether the robot is available."""
        return super().available and bool(self.robot_data.get("available", True))

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        data = self.robot_data
        return DeviceInfo(
            identifiers={(DOMAIN, self.serial)},
            manufacturer="Zodiac",
            model=str(data.get("model") or data.get("device_type") or "Pool Robot"),
            name=str(data.get("name") or "Zodiac Pool Robot"),
            serial_number=self.serial,
            sw_version=str(data.get("robot_firmware") or "") or None,
        )
