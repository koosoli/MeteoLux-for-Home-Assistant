"""Config flow for MeteoLux."""
from __future__ import annotations
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)
from .const import (
    DOMAIN,
    CONF_FORECAST_DAYS,
    DEFAULT_FORECAST_DAYS,
    FORECAST_DAYS_RANGE
)

_LOGGER = logging.getLogger(__name__)

OPTIONS_SCHEMA = vol.Schema({
    vol.Required(CONF_FORECAST_DAYS, default=DEFAULT_FORECAST_DAYS): vol.In(FORECAST_DAYS_RANGE)
})

CONFIG_SCHEMA = vol.Schema({vol.Required("dummy", default=True): bool})


class MeteoluxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeteoLux."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="MeteoLux", data={}, options={CONF_FORECAST_DAYS: DEFAULT_FORECAST_DAYS})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return MeteoluxOptionsFlowHandler(config_entry)


class MeteoluxOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_FORECAST_DAYS,
                        default=self.config_entry.options.get(
                            CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS
                        ),
                    ): vol.In(FORECAST_DAYS_RANGE),
                }
            ),
        )
