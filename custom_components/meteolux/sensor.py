"""Sensor platform for MeteoLux."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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

    value_fn: Callable[[dict], float | str | None] = None


SENSORS: tuple[MeteoluxSensorEntityDescription, ...] = (
    MeteoluxSensorEntityDescription(
        key="temp_max",
        name="Max Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.get("day", {}).get("temp_max"),
    ),
    MeteoluxSensorEntityDescription(
        key="temp_min",
        name="Min Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda data: data.get("day", {}).get("temp_min"),
    ),
    MeteoluxSensorEntityDescription(
        key="morning_precipitation",
        name="Morning Precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        value_fn=lambda data: float(data.get("forecasts", {}).get("morning", {}).get("precipitation", "0").split(" ")[0].replace(",",".")),
    ),
    MeteoluxSensorEntityDescription(
        key="afternoon_precipitation",
        name="Afternoon Precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        value_fn=lambda data: float(data.get("forecasts", {}).get("afternoon", {}).get("precipitation", "0").split(" ")[0].replace(",",".")),
    ),
    MeteoluxSensorEntityDescription(
        key="evening_precipitation",
        name="Evening Precipitation",
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        value_fn=lambda data: float(data.get("forecasts", {}).get("evening", {}).get("precipitation", "0").split(" ")[0].replace(",",".")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MeteoLux sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        MeteoluxSensor(coordinator, description) for description in SENSORS
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
        self._attr_name = f"MeteoLux {description.name}"

    @property
    def native_value(self) -> float | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)
