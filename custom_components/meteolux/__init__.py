"""The MeteoLux integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeteoluxApiClient, MeteoluxApiJsonClient
from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MeteoLux from a config entry."""
    session = async_get_clientsession(hass)
    client: MeteoluxApiClient | MeteoluxApiJsonClient

    if entry.data.get("data_source") == "JSON API":
        client = MeteoluxApiJsonClient(
            session,
            entry.data.get(CONF_LATITUDE),
            entry.data.get(CONF_LONGITUDE),
        )
    else:
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
