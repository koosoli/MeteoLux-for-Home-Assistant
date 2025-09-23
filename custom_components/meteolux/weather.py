"""Weather platform for MeteoLux."""
from __future__ import annotations

from datetime import datetime, time
import logging

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfSpeed, UnitOfPrecipitationDepth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .api import Forecast as MeteoluxForecast, DailyForecast, HourlyForecast
from .const import (
    CONDITION_MAP,
    DOMAIN,
    FORECAST_TIMES,
    CONF_FORECAST_DAYS,
    DEFAULT_FORECAST_DAYS,
)
from .coordinator import MeteoluxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _map_condition(weather_description: str | None) -> str:
    """Map MeteoLux weather description to Home Assistant condition."""
    if not weather_description:
        return "unknown"
    
    # Try exact match first
    if weather_description in CONDITION_MAP:
        return CONDITION_MAP[weather_description]
    
    # Try partial matches for more flexible mapping
    description_lower = weather_description.lower()
    for key, condition in CONDITION_MAP.items():
        if key.lower() in description_lower:
            return condition
    
    return "unknown"


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
    _attr_supported_features = WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY

    def __init__(self, coordinator: MeteoluxDataUpdateCoordinator) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name="MeteoLux",
            manufacturer="MeteoLux",
        )

    @property
    def _current_forecast(self) -> MeteoluxForecast | None:
        """Return the forecast for the current time."""
        now = dt_util.now()
        forecasts = self.coordinator.data.forecasts

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
        if not self.coordinator.data:
            return None
            
        # Try to get condition from current weather (new API)
        if self.coordinator.data.current_weather:
            return _map_condition(self.coordinator.data.current_weather.condition)
        
        # Fallback to legacy forecast data
        if not (current_forecast := self._current_forecast):
            return None
        weather_text = current_forecast.weather
        return CONDITION_MAP.get(weather_text, "unknown")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        if not self.coordinator.data:
            return None
            
        # Try to get from current weather (new API)
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.temperature
        
        # Fallback to legacy data
        return self.coordinator.data.temp_max

    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""
        if not self.coordinator.data:
            return None
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.pressure
        return None

    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        if not self.coordinator.data:
            return None
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.humidity
        return None

    @property
    def visibility(self) -> float | None:
        """Return the visibility."""
        if not self.coordinator.data:
            return None
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.visibility
        return None

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        if not self.coordinator.data:
            return None
            
        # Try to get from current weather (new API)
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.wind_speed
        
        # Fallback to legacy forecast data
        if not (current_forecast := self._current_forecast):
            return None
        return current_forecast.wind_force

    @property
    def wind_bearing(self) -> str | None:
        """Return the wind bearing."""
        if not self.coordinator.data:
            return None
            
        # Try to get from current weather (new API)
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.wind_direction
        
        # Fallback to legacy forecast data
        if not (current_forecast := self._current_forecast):
            return None
        return current_forecast.wind_direction

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        if not self.coordinator.data:
            return None

        # Use new API data if available
        if self.coordinator.data.daily_forecasts is not None:
            forecasts = []
            forecast_days = self.coordinator.config_entry.options.get(
                CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS
            )
            for daily_forecast in self.coordinator.data.daily_forecasts[:forecast_days]:
                if not daily_forecast or not daily_forecast.datetime:
                    continue
                forecast = Forecast(
                    datetime=daily_forecast.datetime.isoformat(),
                    condition=_map_condition(daily_forecast.condition),
                    native_temperature=daily_forecast.temperature_max,
                    native_templow=daily_forecast.temperature_min,
                    native_precipitation=daily_forecast.precipitation,
                    wind_bearing=daily_forecast.wind_direction,
                    native_wind_speed=daily_forecast.wind_speed,
                    humidity=daily_forecast.humidity,
                    native_pressure=daily_forecast.pressure,
                )
                forecasts.append(forecast)
            return forecasts

        # Fallback to legacy data (daily periods)
        return await self.async_forecast_hourly()

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        if not self.coordinator.data:
            return None

        # Use new API data if available
        if self.coordinator.data.hourly_forecasts is not None:
            forecasts = []
            for hourly_forecast in self.coordinator.data.hourly_forecasts[:48]:  # Max 48 hours
                if not hourly_forecast or not hourly_forecast.datetime:
                    continue
                forecast = Forecast(
                    datetime=hourly_forecast.datetime.isoformat(),
                    condition=_map_condition(hourly_forecast.condition),
                    native_temperature=hourly_forecast.temperature,
                    native_precipitation=hourly_forecast.precipitation,
                    wind_bearing=hourly_forecast.wind_direction,
                    native_wind_speed=hourly_forecast.wind_speed,
                    humidity=hourly_forecast.humidity,
                    native_pressure=hourly_forecast.pressure,
                    cloud_coverage=hourly_forecast.cloud_coverage,
                )
                forecasts.append(forecast)
            return forecasts

        # Fallback to legacy data (daily periods)
        if self.coordinator.data.forecasts is None:
            return []

        forecasts = self.coordinator.data.forecasts
        base_date = self.coordinator.data.created.date()

        daily_forecasts = []
        for period, forecast_time in FORECAST_TIMES.items():
            if period_data := forecasts.get(period):
                if not period_data.is_displayed:
                    continue

                forecast_dt = datetime.combine(
                    base_date, forecast_time, tzinfo=dt_util.get_default_timezone()
                )

                forecast = Forecast(
                    datetime=forecast_dt.isoformat(),
                    condition=CONDITION_MAP.get(period_data.weather, "unknown"),
                    native_temperature=period_data.temp_high,
                    native_templow=period_data.temp_low,
                    native_precipitation=period_data.precipitation,
                    wind_bearing=period_data.wind_direction,
                    native_wind_speed=period_data.wind_force,
                )
                daily_forecasts.append(forecast)

        return daily_forecasts
