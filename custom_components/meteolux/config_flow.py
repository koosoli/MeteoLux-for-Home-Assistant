"""Config flow for MeteoLux."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.data_entry_flow import FlowResult

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

        # Check for existing coordinates in Home Assistant config
        if hasattr(self.hass.config, "latitude") and hasattr(
            self.hass.config, "longitude"
        ):
            default_lat = self.hass.config.latitude
            default_lon = self.hass.config.longitude
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_LATITUDE, default=default_lat): float,
                    vol.Required(CONF_LONGITUDE, default=default_lon): float,
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_LATITUDE): float,
                    vol.Required(CONF_LONGITUDE): float,
                }
            )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
        )
