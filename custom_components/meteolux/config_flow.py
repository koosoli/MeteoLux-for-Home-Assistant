"""Config flow for MeteoLux."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

DATA_SOURCE_LEGACY = "Legacy (CSV)"
DATA_SOURCE_JSON = "JSON API"


class MeteoluxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeteoLux."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            data_source = user_input["data_source"]
            
            config_data = {
                "data_source": data_source,
            }
            
            # Only include location data for JSON API
            if data_source == DATA_SOURCE_JSON:
                config_data[CONF_LATITUDE] = user_input[CONF_LATITUDE]
                config_data[CONF_LONGITUDE] = user_input[CONF_LONGITUDE]
                
            return self.async_create_entry(
                title=f"MeteoLux ({data_source})",
                data=config_data,
            )

        latitude = self.hass.config.latitude
        longitude = self.hass.config.longitude

        schema_dict = {
            vol.Required("data_source", default=DATA_SOURCE_LEGACY): vol.In([
                DATA_SOURCE_LEGACY,
                DATA_SOURCE_JSON,
            ]),
        }
        
        # Add location fields (will be shown conditionally in UI)
        schema_dict[vol.Optional(CONF_LATITUDE, default=latitude)] = float
        schema_dict[vol.Optional(CONF_LONGITUDE, default=longitude)] = float

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_dict),
        )
