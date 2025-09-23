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
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MeteoluxData
from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator


@dataclass
class MeteoluxSensorEntityDescription(SensorEntityDescription):
    """Describes a MeteoLux sensor entity."""

    value_fn: Callable[[MeteoluxData], float | str | None] = None
    available_fn: Callable[[MeteoluxData], bool] = lambda data: True


def get_forecast_value_fn(period: str, key: str) -> Callable[[MeteoluxData], Any]:
    """Create a value_fn to get a value from a specific forecast period."""
    return lambda data: getattr(data.forecasts.get(period), key, None)


def get_forecast_available_fn(period: str) -> Callable[[MeteoluxData], bool]:
    """Create an available_fn to check if a forecast period is available."""
    return (
        lambda data: data.forecasts.get(period) is not None
        and data.forecasts.get(period).is_displayed
    )


SENSORS: tuple[MeteoluxSensorEntityDescription, ...] = (
    MeteoluxSensorEntityDescription(
        key="temp_max",
        translation_key="temp_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.temp_max,
    ),
    MeteoluxSensorEntityDescription(
        key="temp_min",
        translation_key="temp_min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.temp_min,
    ),
)

# JSON API specific sensors
JSON_API_SENSORS: tuple[MeteoluxSensorEntityDescription, ...] = (
    MeteoluxSensorEntityDescription(
        key="sunshine",
        translation_key="sunshine",
        native_unit_of_measurement="h",
        icon="mdi:weather-sunny",
        value_fn=lambda data: next(
            (forecast.sunshine for forecast in data.forecasts.values() if forecast.sunshine is not None), 
            None
        ),
        available_fn=lambda data: any(forecast.sunshine is not None for forecast in data.forecasts.values()),
    ),
    MeteoluxSensorEntityDescription(
        key="uv_index",
        translation_key="uv_index",
        icon="mdi:sun-wireless",
        value_fn=lambda data: next(
            (forecast.uv_index for forecast in data.forecasts.values() if forecast.uv_index is not None), 
            None
        ),
        available_fn=lambda data: any(forecast.uv_index is not None for forecast in data.forecasts.values()),
    ),
)

FORECAST_SENSORS: tuple[MeteoluxSensorEntityDescription, ...] = (
    MeteoluxSensorEntityDescription(
        key="temp_low",
        translation_key="temp_low",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    MeteoluxSensorEntityDescription(
        key="temp_high",
        translation_key="temp_high",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    MeteoluxSensorEntityDescription(
        key="precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        icon="mdi:weather-rainy",
    ),
    MeteoluxSensorEntityDescription(
        key="wind_force",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        icon="mdi:weather-windy",
    ),
    MeteoluxSensorEntityDescription(
        key="wind_gusts",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        icon="mdi:weather-windy-variant",
    ),
    MeteoluxSensorEntityDescription(
        key="wind_direction",
        icon="mdi:compass-outline",
    ),
    MeteoluxSensorEntityDescription(
        key="weather",
        icon="mdi:card-text-outline",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MeteoLux sensor platform."""
    coordinator: MeteoluxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [MeteoluxSensor(coordinator, description) for description in SENSORS]

    # Add JSON API specific sensors if using JSON API
    data_source = entry.data.get("data_source", "Legacy (CSV)")
    if data_source == "JSON API":
        entities.extend([MeteoluxSensor(coordinator, description) for description in JSON_API_SENSORS])

    for period in ("morning", "afternoon", "evening"):
        for description in FORECAST_SENSORS:
            entities.append(
                MeteoluxSensor(
                    coordinator,
                    MeteoluxSensorEntityDescription(
                        key=f"{period}_{description.key}",
                        translation_key=f"{period}_{description.key}",
                        native_unit_of_measurement=description.native_unit_of_measurement,
                        device_class=description.device_class,
                        icon=description.icon,
                        value_fn=get_forecast_value_fn(period, description.key),
                        available_fn=get_forecast_available_fn(period),
                    ),
                )
            )

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
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="MeteoLux",
            manufacturer="MeteoLux",
        )

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.entity_description.value_fn(self.coordinator.data)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.available_fn(self.coordinator.data)
        )
