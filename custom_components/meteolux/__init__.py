"""The MeteoLux integration."""
from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeteoluxApiClient
from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


from .const import CONF_LANGUAGE, DEFAULT_LANGUAGE

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MeteoLux from a config entry."""
    session = async_get_clientsession(hass)
    language = entry.options.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    client = MeteoluxApiClient(session, hass.config.latitude, hass.config.longitude, language)

    coordinator = MeteoluxDataUpdateCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
