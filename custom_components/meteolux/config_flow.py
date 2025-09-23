"""Config flow for MeteoLux."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, FlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .const import DOMAIN


class MeteoluxConfigFlow(ConfigFlow):
    """Handle a config flow for MeteoLux."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="MeteoLux",
                data={
                    CONF_LATITUDE: user_input[CONF_LATITUDE],
                    CONF_LONGITUDE: user_input[CONF_LONGITUDE],
                },
            )

        latitude = self.hass.config.latitude
        longitude = self.hass.config.longitude

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LATITUDE, default=latitude
                    ): float,
                    vol.Required(
                        CONF_LONGITUDE, default=longitude
                    ): float,
                }
            ),
        )
