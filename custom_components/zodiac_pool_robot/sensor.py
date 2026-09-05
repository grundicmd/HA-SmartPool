"""Sensors for Zodiac Pool Robot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import UnitOfTime
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import ZodiacConfigEntry
from .entity import ZodiacEntity


@dataclass(frozen=True, kw_only=True)
class ZodiacSensorDescription(SensorEntityDescription):
    """Describe a Zodiac sensor."""

    data_key: str


SENSORS = (
    ZodiacSensorDescription(
        key="total_runtime",
        translation_key="total_runtime",
        data_key="total_runtime_hours",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:timer-outline",
    ),
    ZodiacSensorDescription(
        key="remaining_time",
        translation_key="remaining_time",
        data_key="remaining_minutes",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-sand",
    ),
    ZodiacSensorDescription(
        key="last_error",
        translation_key="last_error",
        data_key="error",
        icon="mdi:alert-circle-outline",
    ),
    ZodiacSensorDescription(
        key="canister",
        translation_key="canister",
        data_key="canister",
        icon="mdi:filter-outline",
    ),
)


async def async_setup_entry(
    hass: Any,
    entry: ZodiacConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Zodiac sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        ZodiacSensor(coordinator, str(device["serial_number"]), description)
        for device in coordinator.devices
        for description in SENSORS
    )


class ZodiacSensor(ZodiacEntity, SensorEntity):
    """A sensor backed by normalized robot data."""

    entity_description: ZodiacSensorDescription

    def __init__(
        self, coordinator: Any, serial: str, description: ZodiacSensorDescription
    ) -> None:
        super().__init__(coordinator, serial, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        return self.robot_data.get(self.entity_description.data_key)
