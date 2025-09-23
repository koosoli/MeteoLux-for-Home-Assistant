"""Config flow for MeteoLux."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DOMAIN

DATA_SOURCE_OPTIONS = ["Legacy (CSV)", "JSON API"]


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
            if user_input["data_source"] == "Legacy (CSV)":
                return self.async_create_entry(title="MeteoLux", data=user_input)
            return await self.async_step_location()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("data_source"): SelectSelector(
                        SelectSelectorConfig(
                            options=DATA_SOURCE_OPTIONS,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the location step."""
        if user_input is not None:
            return self.async_create_entry(
                title="MeteoLux",
                data={
                    "data_source": "JSON API",
                    CONF_LATITUDE: user_input[CONF_LATITUDE],
                    CONF_LONGITUDE: user_input[CONF_LONGITUDE],
                },
            )

        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LATITUDE, default=self.hass.config.latitude
                    ): float,
                    vol.Required(
                        CONF_LONGITUDE, default=self.hass.config.longitude
                    ): float,
                }
            ),
        )
