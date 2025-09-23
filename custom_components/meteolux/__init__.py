"""The MeteoLux integration."""
from __future__ import annotations

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeteoluxApiClient, MeteoluxApiJsonClient
from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MeteoLux from a config entry."""
    session = async_get_clientsession(hass)
    
    # Choose the appropriate client based on configuration
    data_source = entry.data.get("data_source", "Legacy (CSV)")
    
    if data_source == "JSON API":
        # Get location from config
        latitude = entry.data.get("latitude", 49.6116)  # Default to Luxembourg City
        longitude = entry.data.get("longitude", 6.1319)
        client = MeteoluxApiJsonClient(session, latitude, longitude)
    else:
        # Use legacy CSV API
        client = MeteoluxApiClient(session)

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
