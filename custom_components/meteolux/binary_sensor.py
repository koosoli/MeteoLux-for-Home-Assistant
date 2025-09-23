"""Binary sensor platform for MeteoLux."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MeteoLux binary sensor platform."""
    coordinator: MeteoluxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoalarmAlert(coordinator)])


class MeteoalarmAlert(CoordinatorEntity[MeteoluxDataUpdateCoordinator], BinarySensorEntity):
    """Meteoalarm alert binary sensor."""

    _attr_has_entity_name = True
    _attr_translation_key = "meteoalarm_alert"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator: MeteoluxDataUpdateCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_meteoalarm_alert"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="MeteoLux",
            manufacturer="MeteoLux",
        )
        self._alert = None

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        # The coordinator data is not used for this sensor, as it fetches data from a different source.
        # However, we still use the coordinator to trigger updates.
        # We will fetch the data in the _update_alert method.
        return self._alert is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self._alert:
            return None
        return {
            "awareness_level": self._alert.awareness_level,
            "awareness_type": self._alert.awareness_type,
            "awareness_description": self._alert.awareness_description,
            "start": self._alert.start,
            "end": self._alert.end,
            "link": self._alert.link,
        }

    async def async_update(self) -> None:
        """Update the entity.

        This method is called by the coordinator when a new update is available.
        """
        from meteoalertapi import Meteoalert

        try:
            client = Meteoalert("LU", "fr")
            self._alert = await self.hass.async_to_executor_thread(client.get_alert)
        except Exception:
            self._alert = None
