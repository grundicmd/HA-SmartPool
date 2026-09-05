"""Config flow for Zodiac Pool Robot."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import ZodiacApiError, ZodiacAuthError, ZodiacClient, ZodiacConnectionError
from .const import DOMAIN, SUPPORTED_DEVICE_TYPES


class ZodiacPoolRobotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Zodiac Pool Robot config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(email)
            self._abort_if_unique_id_configured()
            client = ZodiacClient(
                async_get_clientsession(self.hass),
                email,
                user_input[CONF_PASSWORD],
            )
            try:
                await client.async_login()
                devices = await client.async_list_devices()
            except ZodiacAuthError:
                errors["base"] = "invalid_auth"
            except ZodiacConnectionError:
                errors["base"] = "cannot_connect"
            except ZodiacApiError:
                errors["base"] = "unknown"
            else:
                supported = [
                    device
                    for device in devices
                    if device.get("device_type") in SUPPORTED_DEVICE_TYPES
                ]
                if not supported:
                    errors["base"] = "no_supported_devices"
                else:
                    title = (
                        str(supported[0].get("name") or "Zodiac Pool Robot")
                        if len(supported) == 1
                        else "Zodiac Pool Robots"
                    )
                    return self.async_create_entry(
                        title=title,
                        data={CONF_EMAIL: email, CONF_PASSWORD: user_input[CONF_PASSWORD]},
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_EMAIL): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.EMAIL)
                ),
                vol.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
