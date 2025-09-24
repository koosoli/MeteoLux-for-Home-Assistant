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
from .const import DOMAIN, DEFAULT_FORECAST_DAYS
from .coordinator import MeteoluxDataUpdateCoordinator


@dataclass
class MeteoluxSensorEntityDescription(SensorEntityDescription):
    """Describes a MeteoLux sensor entity."""

    value_fn: Callable[..., float | str | None] = None
    attributes_fn: Callable[[MeteoluxData], dict[str, Any]] | None = None
    available_fn: Callable[[MeteoluxData], bool] = lambda data: True


def _get_vigilance_level(data: MeteoluxData) -> str | int:
    """Get the highest vigilance level."""
    if not data.vigilances:
        return "none"

    highest_level = 0
    for v in data.vigilances:
        if v.level and v.level > highest_level:
            highest_level = v.level

    return highest_level if highest_level > 0 else "none"


def _get_vigilance_attributes(data: MeteoluxData) -> dict[str, Any]:
    """Get the attributes for the vigilance sensor."""
    if not data.vigilances:
        return {}

    highest_vigilance = None
    highest_level = 0
    for v in data.vigilances:
        if v.level and v.level > highest_level:
            highest_level = v.level
            highest_vigilance = v

    if not highest_vigilance:
        return {}

    return {
        "description": highest_vigilance.description,
        "start_time": highest_vigilance.datetime_start.isoformat()
        if highest_vigilance.datetime_start
        else None,
        "end_time": highest_vigilance.datetime_end.isoformat()
        if highest_vigilance.datetime_end
        else None,
        "type": highest_vigilance.type,
        "region": highest_vigilance.region,
        "active_warnings": len(data.vigilances),
    }


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
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.created.isoformat(),
    ),
    MeteoluxSensorEntityDescription(
        key="data_source",
        translation_key="data_source",
        value_fn=lambda data: data.data_source,
    ),
    MeteoluxSensorEntityDescription(
        key="api_endpoint",
        translation_key="api_endpoint",
        value_fn=lambda data: data.api_endpoint_used,
    ),
    MeteoluxSensorEntityDescription(
        key="daily_forecasts",
        translation_key="daily_forecasts",
        value_fn=lambda data: len(data.daily_forecasts) if data.daily_forecasts else 0,
    ),
    MeteoluxSensorEntityDescription(
        key="hourly_forecasts",
        translation_key="hourly_forecasts",
        value_fn=lambda data: len(data.hourly_forecasts) if data.hourly_forecasts else 0,
    ),
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
    MeteoluxSensorEntityDescription(
        key="vigilance_level",
        translation_key="vigilance_level",
        icon="mdi:alert-outline",
        value_fn=_get_vigilance_level,
        attributes_fn=_get_vigilance_attributes,
        available_fn=lambda data: data.vigilances is not None,
    ),
)

FORECAST_SENSORS: tuple[MeteoluxSensorEntityDescription, ...] = (
    MeteoluxSensorEntityDescription(
        key="temp_max",
        translation_key="day_temp_max",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data, day: data.daily_forecasts[day].temperature_max,
    ),
    MeteoluxSensorEntityDescription(
        key="temp_min",
        translation_key="day_temp_min",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data, day: data.daily_forecasts[day].temperature_min,
    ),
    MeteoluxSensorEntityDescription(
        key="precipitation",
        translation_key="day_precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        icon="mdi:weather-rainy",
        value_fn=lambda data, day: data.daily_forecasts[day].precipitation,
    ),
    MeteoluxSensorEntityDescription(
        key="wind_speed",
        translation_key="day_wind_speed",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        icon="mdi:weather-windy",
        value_fn=lambda data, day: data.daily_forecasts[day].wind_speed,
    ),
    MeteoluxSensorEntityDescription(
        key="wind_gusts",
        translation_key="day_wind_gusts",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        icon="mdi:weather-windy-variant",
        value_fn=lambda data, day: data.daily_forecasts[day].wind_gusts,
    ),
    MeteoluxSensorEntityDescription(
        key="wind_direction",
        translation_key="day_wind_direction",
        icon="mdi:compass-outline",
        value_fn=lambda data, day: data.daily_forecasts[day].wind_direction,
    ),
    MeteoluxSensorEntityDescription(
        key="condition",
        translation_key="day_condition",
        icon="mdi:card-text-outline",
        value_fn=lambda data, day: data.daily_forecasts[day].condition,
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

    configured_forecast_days = entry.options.get(
        "forecast_days", DEFAULT_FORECAST_DAYS
    )

    available_forecasts = 0
    if coordinator.data and coordinator.data.daily_forecasts:
        available_forecasts = len(coordinator.data.daily_forecasts)

    # Create sensors only for the available forecast days, up to the configured limit
    for day in range(min(configured_forecast_days, available_forecasts)):
        for description in FORECAST_SENSORS:
            entities.append(
                MeteoluxDaySensor(
                    coordinator,
                    day,
                    MeteoluxSensorEntityDescription(
                        key=f"day_{day+1}_{description.key}",
                        translation_key=description.translation_key,
                        native_unit_of_measurement=description.native_unit_of_measurement,
                        device_class=description.device_class,
                        icon=description.icon,
                        value_fn=description.value_fn,
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
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.coordinator.data and self.entity_description.attributes_fn:
            return self.entity_description.attributes_fn(self.coordinator.data)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data is not None
            and self.entity_description.available_fn(self.coordinator.data)
        )


class MeteoluxDaySensor(MeteoluxSensor):
    """MeteoLux day sensor entity."""

    def __init__(
        self,
        coordinator: MeteoluxDataUpdateCoordinator,
        day: int,
        description: MeteoluxSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description)
        self._day = day
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_translation_placeholders = {"day": str(day + 1)}

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.entity_description.value_fn(self.coordinator.data, self._day)
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            super().available
            and self.coordinator.data.daily_forecasts is not None
            and len(self.coordinator.data.daily_forecasts) > self._day
        )
