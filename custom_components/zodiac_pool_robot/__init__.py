"""Zodiac Pool Robot integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import ZodiacApiError, ZodiacAuthError, ZodiacClient
from .const import DOMAIN, PLATFORMS, SUPPORTED_DEVICE_TYPES
from .coordinator import ZodiacCoordinator


@dataclass
class ZodiacRuntimeData:
    """Runtime data shared by Zodiac entities."""

    client: ZodiacClient
    coordinator: ZodiacCoordinator


type ZodiacConfigEntry = ConfigEntry[ZodiacRuntimeData]


async def async_setup_entry(hass: HomeAssistant, entry: ZodiacConfigEntry) -> bool:
    """Set up Zodiac Pool Robot from a config entry."""
    client = ZodiacClient(
        async_get_clientsession(hass),
        entry.data[CONF_EMAIL],
        entry.data[CONF_PASSWORD],
    )
    try:
        await client.async_login()
        devices = [
            device
            for device in await client.async_list_devices()
            if device.get("device_type") in SUPPORTED_DEVICE_TYPES
        ]
    except ZodiacAuthError as err:
        raise ConfigEntryAuthFailed from err
    except ZodiacApiError as err:
        raise ConfigEntryNotReady(str(err)) from err
    coordinator = ZodiacCoordinator(hass, client, devices)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = ZodiacRuntimeData(client, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ZodiacConfigEntry) -> bool:
    """Unload a Zodiac Pool Robot config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
