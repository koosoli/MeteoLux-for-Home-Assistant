"""Sensor platform for MeteoLux."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfSpeed,
    UnitOfPrecipitationDepth,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator


@dataclass
class MeteoluxSensorEntityDescription(SensorEntityDescription):
    """Describes a MeteoLux sensor entity."""
    value_fn: Callable[[dict[str, Any]], float | str | None] = None


def get_forecast_value_fn(period: str, key: str) -> Callable[[dict[str, Any]], Any]:
    """Create a value_fn to get a value from a specific forecast period."""
    return lambda data: data.get("forecasts", {}).get(period, {}).get(key)


SENSORS: tuple[MeteoluxSensorEntityDescription, ...] = (
    MeteoluxSensorEntityDescription(
        key="temp_max",
        translation_key="temp_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.get("day", {}).get("temp_max"),
    ),
    MeteoluxSensorEntityDescription(
        key="temp_min",
        translation_key="temp_min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.get("day", {}).get("temp_min"),
    ),
    *(
        MeteoluxSensorEntityDescription(
            key=f"{period}_{key}",
            translation_key=f"{period}_{key}",
            native_unit_of_measurement=unit,
            device_class=device_class,
            icon=icon,
            value_fn=get_forecast_value_fn(period, key),
        )
        for period in ("morning", "afternoon", "evening")
        for key, unit, device_class, icon in (
            ("precipitation", UnitOfPrecipitationDepth.MILLIMETERS, SensorDeviceClass.PRECIPITATION, "mdi:weather-rainy"),
            ("wind_force", UnitOfSpeed.KILOMETERS_PER_HOUR, SensorDeviceClass.WIND_SPEED, "mdi:weather-windy"),
            ("wind_gusts", UnitOfSpeed.KILOMETERS_PER_HOUR, SensorDeviceClass.WIND_SPEED, "mdi:weather-windy-variant"),
            ("wind_direction", None, None, "mdi:compass-outline"),
            ("weather", None, None, "mdi:card-text-outline"),
        )
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MeteoLux sensor platform."""
    coordinator: MeteoluxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        MeteoluxSensor(coordinator, description)
        for description in SENSORS
    ]
    async_add_entities(entities)


class MeteoluxSensor(CoordinatorEntity[MeteoluxDataUpdateCoordinator], SensorEntity):
    """MeteoLux sensor entity."""

    entity_description: MeteoluxSensorEntityDescription

    def __init__(
        self,
        coordinator: MeteoluxDataUpdateCoordinator,
        description: MeteoluxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.entity_description.value_fn(self.coordinator.data)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self.native_value is not None
