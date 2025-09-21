"""Weather platform for MeteoLux."""
from __future__ import annotations

from datetime import datetime, time
import logging
from typing import Any

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
from homeassistant.util import dt as dt_util

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
    # Add French conditions if needed, assuming API can be multilingual
    "Ciel dégagé": "sunny",
    "Partiellement nuageux": "partlycloudy",
    "Nuageux": "cloudy",
    "Couvert": "cloudy",
    "Pluie faible": "rainy",
    "Pluie modérée": "rainy",
    "Pluie forte": "pouring",
    "Bruine": "rainy",
    "Brouillard": "fog",
    "Neige": "snowy",
    "Neige fondue": "sleet",
}

FORECAST_TIMES = {
    "morning": time(8, 0, 0),
    "afternoon": time(14, 0, 0),
    "evening": time(20, 0, 0),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the MeteoLux weather platform."""
    coordinator: MeteoluxDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoluxWeather(coordinator)])


class MeteoluxWeather(CoordinatorEntity[MeteoluxDataUpdateCoordinator], WeatherEntity):
    """MeteoLux weather entity."""

    _attr_has_entity_name = True
    _attr_translation_key = "meteolux"
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_supported_features = WeatherEntityFeature.FORECAST_TWICE_DAILY

    def __init__(self, coordinator: MeteoluxDataUpdateCoordinator) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"

    @property
    def _current_forecast(self) -> dict[str, Any] | None:
        """Return the forecast for the current time."""
        now = dt_util.now()
        forecasts = self.coordinator.data.get("forecasts", {})

        # Determine which forecast period is most relevant
        if now.hour < 12 and "morning" in forecasts:
            return forecasts["morning"]
        if now.hour < 18 and "afternoon" in forecasts:
            return forecasts["afternoon"]
        if "evening" in forecasts:
            return forecasts["evening"]

        # Fallback to the first available forecast
        if forecasts:
            return next(iter(forecasts.values()))

        return None

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        if not (current_forecast := self._current_forecast):
            return None
        weather_text = current_forecast.get("weather")
        return CONDITION_MAP.get(weather_text, "unknown")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        # The API provides day min/max, not a current temperature.
        # We can use the max temp for the day as the primary temperature.
        return self.coordinator.data.get("day", {}).get("temp_max")

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        if not (current_forecast := self._current_forecast):
            return None
        return current_forecast.get("wind_force")

    @property
    def wind_bearing(self) -> str | None:
        """Return the wind bearing."""
        if not (current_forecast := self._current_forecast):
            return None
        return current_forecast.get("wind_direction")

    async def async_forecast_twice_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        if not self.coordinator.data:
            return None

        forecasts = self.coordinator.data.get("forecasts", {})
        base_date = self.coordinator.data.get("created", dt_util.now()).date()

        twice_daily_forecasts = []
        for period, forecast_time in FORECAST_TIMES.items():
            if period_data := forecasts.get(period):
                if not period_data.get("is_displayed"):
                    continue

                forecast_dt = datetime.combine(base_date, forecast_time, tzinfo=dt_util.get_default_timezone())

                # The API gives a temp_range for each period, e.g. "15 to 17"
                # We will parse this to get a high and low for the period.
                temp_range_str = period_data.get("temp_range", "")
                temp_low, temp_high = None, None
                if " to " in temp_range_str:
                    low_str, high_str = temp_range_str.split(" to ")
                    try:
                        temp_low = float(low_str)
                        temp_high = float(high_str)
                    except ValueError:
                        pass # Keep them as None

                forecast = Forecast(
                    datetime=forecast_dt.isoformat(),
                    condition=CONDITION_MAP.get(period_data.get("weather"), "unknown"),
                    native_temperature=temp_high,
                    native_templow=temp_low,
                    native_precipitation=period_data.get("precipitation"),
                    wind_bearing=period_data.get("wind_direction"),
                    native_wind_speed=period_data.get("wind_force"),
                )
                twice_daily_forecasts.append(forecast)

        return twice_daily_forecasts
