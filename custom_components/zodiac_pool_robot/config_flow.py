"""Config flow for Zodiac Pool Robot."""

from __future__ import annotations

from collections.abc import Mapping
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

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when iAquaLink credentials are rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate a new password and reload the existing config entry."""
        reauth_entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            client = ZodiacClient(
                async_get_clientsession(self.hass),
                reauth_entry.data[CONF_EMAIL],
                user_input[CONF_PASSWORD],
            )
            try:
                await client.async_login()
            except ZodiacAuthError:
                errors["base"] = "invalid_auth"
            except ZodiacConnectionError:
                errors["base"] = "cannot_connect"
            except ZodiacApiError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            errors=errors,
            description_placeholders={"email": reauth_entry.data[CONF_EMAIL]},
        )
