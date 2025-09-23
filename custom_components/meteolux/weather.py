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

from .api import MeteoluxData
from .const import CONDITION_MAP, DOMAIN, FORECAST_TIMES
from .coordinator import MeteoluxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


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
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_HOURLY | WeatherEntityFeature.FORECAST_DAILY
    )

    def __init__(self, coordinator: MeteoluxDataUpdateCoordinator) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_weather"
        name = f"MeteoLux - {self.coordinator.data.city}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=name,
            manufacturer="MeteoLux",
        )

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        if not self.coordinator.data.current_weather:
            return None
        return CONDITION_MAP.get(self.coordinator.data.current_weather.weather, "unknown")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        if self.coordinator.data.current_weather:
            return self.coordinator.data.current_weather.temp_high
        return self.coordinator.data.temp_max

    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        if not self.coordinator.data.current_weather:
            return None
        return self.coordinator.data.current_weather.wind_force

    @property
    def wind_bearing(self) -> str | None:
        """Return the wind bearing."""
        if not self.coordinator.data.current_weather:
            return None
        return self.coordinator.data.current_weather.wind_direction

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        """Return the hourly forecast."""
        if not self.coordinator.data:
            return None

        # The new API does not provide hourly forecasts, so we return None
        if self.coordinator.data.city:
            return None

        # Legacy forecast
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

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        if not self.coordinator.data or not self.coordinator.data.city:
            return None

        forecasts = []
        for period_data in self.coordinator.data.forecasts.values():
            forecast = Forecast(
                datetime=period_data.datetime.isoformat(),
                condition=CONDITION_MAP.get(period_data.weather, "unknown"),
                native_temperature=period_data.temp_high,
                native_templow=period_data.temp_low,
                wind_bearing=period_data.wind_direction,
                native_wind_speed=period_data.wind_force,
            )
            forecasts.append(forecast)
        return forecasts
