"""Weather platform for MeteoLux."""
from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfSpeed, UnitOfPrecipitationDepth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeteoluxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

CONDITION_MAP = {
    "Clear sky": "sunny",
    "Partly cloudy": "partlycloudy",
    "Cloudy": "cloudy",
    "Overcast": "cloudy",
    "Light rain": "rainy",
    "Moderate rain": "rainy",
    "Heavy rain": "pouring",
    "Drizzle": "rainy",
    "Fog": "fog",
    "Snow": "snowy",
    "Sleet": "sleet",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MeteoLux weather platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoluxWeather(coordinator)])


class MeteoluxWeather(CoordinatorEntity[MeteoluxDataUpdateCoordinator], WeatherEntity):
    """MeteoLux weather entity."""

    _attr_has_entity_name = True
    _attr_name = "MeteoLux"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS # from l/m2
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_supported_features = WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, coordinator: MeteoluxDataUpdateCoordinator) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        afternoon_forecast = self.coordinator.data.get("forecasts", {}).get("afternoon", {})
        weather_text = afternoon_forecast.get("weather")
        return CONDITION_MAP.get(weather_text, "unknown")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        return self.coordinator.data.get("day", {}).get("temp_max")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        afternoon_forecast = self.coordinator.data.get("forecasts", {}).get("afternoon", {})
        wind_force = afternoon_forecast.get("wind_force", "")
        if "to" in wind_force:
            # e.g. "10 to 20"
            return float(wind_force.split(" to ")[1])
        if "-" in wind_force: # e.g. 05-10 km/h
            return float(wind_force.split("-")[1].replace("km/h", "").strip())
        if wind_force:
            return float(wind_force.replace("km/h", "").strip())
        return None

    @property
    def wind_bearing(self) -> str | None:
        """Return the wind bearing."""
        afternoon_forecast = self.coordinator.data.get("forecasts", {}).get("afternoon", {})
        return afternoon_forecast.get("wind_direction")

    async def async_forecast_daily(self) -> list[Forecast]:
        """Return the daily forecast."""
        forecasts = self.coordinator.data.get("forecasts", {})
        daily_forecast = []

        # We only have one day of forecast, split into parts.
        # We'll create a single forecast for the day.
        if forecasts:
            day_data = self.coordinator.data.get("day", {})

            # Use afternoon forecast as the most representative
            afternoon_forecast = forecasts.get("afternoon", {})

            precipitation_str = afternoon_forecast.get("precipitation", "0")
            try:
                # e.g., "1 to 2" -> 2, or "1" -> 1
                precipitation = float(precipitation_str.split(" to ")[-1])
            except (ValueError, IndexError):
                precipitation = 0.0

            forecast = Forecast(
                datetime=datetime.now(),
                condition=CONDITION_MAP.get(afternoon_forecast.get("weather"), "unknown"),
                native_temperature=day_data.get("temp_max"),
                native_templow=day_data.get("temp_min"),
                native_precipitation=precipitation,
                wind_bearing=afternoon_forecast.get("wind_direction"),
            )
            daily_forecast.append(forecast)

        return daily_forecast
