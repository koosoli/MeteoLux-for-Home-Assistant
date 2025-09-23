"""API client for MeteoLux."""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Self

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ClientResponseError

from .const import DATA_URL, WEATHER_ENDPOINT, METAPP_WEATHER_ENDPOINT

_LOGGER = logging.getLogger(__name__)


@dataclass
class DailyForecast:
    """Class for holding daily forecast data."""
    
    datetime: datetime
    condition: str | None
    temperature_max: float | None
    temperature_min: float | None
    precipitation: float | None
    wind_speed: float | None
    wind_direction: str | None
    humidity: float | None
    pressure: float | None


@dataclass
class HourlyForecast:
    """Class for holding hourly forecast data."""
    
    datetime: datetime
    condition: str | None
    temperature: float | None
    precipitation: float | None
    wind_speed: float | None
    wind_direction: str | None
    humidity: float | None
    pressure: float | None
    cloud_coverage: float | None


@dataclass
class CurrentWeather:
    """Class for holding current weather data."""
    
    datetime: datetime
    condition: str | None
    temperature: float | None
    humidity: float | None
    pressure: float | None
    wind_speed: float | None
    wind_direction: str | None
    visibility: float | None


@dataclass
class MeteoluxData:
    """Class for holding MeteoLux data."""

    created: datetime
    temp_min: float | None
    temp_max: float | None
    forecasts: dict[str, Forecast]
    current_weather: CurrentWeather | None = None
    daily_forecasts: list[DailyForecast] | None = None
    hourly_forecasts: list[HourlyForecast] | None = None

    @classmethod
    def from_raw(cls, raw_data: dict[str, str]) -> Self:
        """Parse raw CSV data into a MeteoluxData object."""
        created_str = raw_data.get("created")
        if not created_str:
            raise ValueError("Missing 'created' timestamp")

        data = {
            "created": datetime.strptime(created_str, "%d-%m-%Y %H:%M:%S"),
            "temp_min": _parse_float(raw_data.get("temp_min")),
            "temp_max": _parse_float(raw_data.get("temp_max")),
            "forecasts": {},
        }

        for i in range(1, 4):  # For morning, afternoon, evening
            prefix = f"{i}_"
            if f"{prefix}is_displayed" not in raw_data:
                continue

            title = raw_data.get(f"{prefix}title", "").lower()
            if not title:
                continue

            temp_low, temp_high = _parse_temp_range(raw_data.get(f"{prefix}temp_range"))

            data["forecasts"][title] = Forecast(
                is_displayed=raw_data.get(f"{prefix}is_displayed") == "1",
                weather=raw_data.get(f"{prefix}weather"),
                icon=raw_data.get(f"{prefix}icon"),
                temp_range=raw_data.get(f"{prefix}temp_range"),
                temp_low=temp_low,
                temp_high=temp_high,
                precipitation=_parse_precipitation(
                    raw_data.get(f"{prefix}precipitation")
                ),
                wind_direction=raw_data.get(f"{prefix}wind_direction_tooltip"),
                wind_force=_parse_wind_force(raw_data.get(f"{prefix}wind_force")),
                wind_gusts=_parse_wind_force(raw_data.get(f"{prefix}wind_gusts")),
            )
        return cls(**data)

    @classmethod
    def from_api_response(cls, api_data: dict[str, Any]) -> Self:
        """Parse API response data into a MeteoluxData object."""
        created = datetime.now()
        current = api_data.get("current", {})
        
        # Parse current weather
        current_weather = CurrentWeather(
            datetime=created,
            condition=current.get("weather", {}).get("description"),
            temperature=current.get("temperature"),
            humidity=current.get("humidity"),
            pressure=current.get("pressure"),
            wind_speed=current.get("wind", {}).get("speed"),
            wind_direction=current.get("wind", {}).get("direction"),
            visibility=current.get("visibility"),
        )

        # Parse daily forecasts
        daily_forecasts = []
        for day_data in api_data.get("daily", []):
            if "datetime" in day_data:
                daily_forecasts.append(DailyForecast(
                    datetime=datetime.fromisoformat(day_data["datetime"]),
                    condition=day_data.get("weather", {}).get("description"),
                    temperature_max=day_data.get("temperature", {}).get("max"),
                    temperature_min=day_data.get("temperature", {}).get("min"),
                    precipitation=day_data.get("precipitation"),
                    wind_speed=day_data.get("wind", {}).get("speed"),
                    wind_direction=day_data.get("wind", {}).get("direction"),
                    humidity=day_data.get("humidity"),
                    pressure=day_data.get("pressure"),
                ))

        # Parse hourly forecasts
        hourly_forecasts = []
        for hour_data in api_data.get("hourly", []):
            if "datetime" in hour_data:
                hourly_forecasts.append(HourlyForecast(
                    datetime=datetime.fromisoformat(hour_data["datetime"]),
                    condition=hour_data.get("weather", {}).get("description"),
                    temperature=hour_data.get("temperature"),
                    precipitation=hour_data.get("precipitation"),
                    wind_speed=hour_data.get("wind", {}).get("speed"),
                    wind_direction=hour_data.get("wind", {}).get("direction"),
                    humidity=hour_data.get("humidity"),
                    pressure=hour_data.get("pressure"),
                    cloud_coverage=hour_data.get("cloud_coverage"),
                ))

        return cls(
            created=created,
            temp_min=current.get("temperature"),
            temp_max=current.get("temperature"),
            forecasts={},  # Keep legacy format for compatibility
            current_weather=current_weather,
            daily_forecasts=daily_forecasts,
            hourly_forecasts=hourly_forecasts,
        )


@dataclass
class Forecast:
    """Class for holding forecast data."""

    is_displayed: bool
    weather: str | None
    icon: str | None
    temp_range: str | None
    temp_low: float | None
    temp_high: float | None
    precipitation: float | None
    wind_direction: str | None
    wind_force: float | None
    wind_gusts: float | None


class MeteoluxApiClientError(Exception):
    """Exception to indicate a general API error."""


class MeteoluxApiConnectionError(MeteoluxApiClientError):
    """Exception to indicate a connection error."""


def _parse_float(value: str | None, decimal_separator: str = ".") -> float | None:
    """Parse a float from a string, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value.replace(decimal_separator, ",").replace(",", "."))
    except (ValueError, TypeError):
        return None


def _parse_range(value: str | None) -> list[float | None]:
    """Parse a range string (e.g., '5-10') and return a list of floats."""
    if value is None:
        return [None, None]
    parts = value.replace(",", ".").strip().split("-")
    if len(parts) > 1:
        return [_parse_float(parts[0]), _parse_float(parts[-1])]
    if len(parts) == 1:
        return [_parse_float(parts[0]), _parse_float(parts[0])]
    return [None, None]


def _parse_temp_range(value: str | None) -> tuple[float | None, float | None]:
    """Parse temp range string (e.g., '12 to 14') and return low and high."""
    if value is None:
        return None, None
    parts = value.lower().split(" to ")
    if len(parts) == 2:
        return _parse_float(parts[0]), _parse_float(parts[1])
    return None, None


def _parse_precipitation(value: str | None) -> float | None:
    """Parse precipitation string (e.g., '7-9 l/m²') and return the higher value in mm."""
    if value is None:
        return None
    cleaned_value = value.split(" ")[0]
    _, high = _parse_range(cleaned_value)
    return high


def _parse_wind_force(value: str | None) -> float | None:
    """Parse wind force string (e.g., '05-10 km/h') and return the higher value."""
    if value is None:
        return None
    cleaned_value = value.split(" ")[0]
    _, high = _parse_range(cleaned_value)
    return high


class MeteoluxApiClient:
    """MeteoLux API client."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the client."""
        self._session = session

    async def async_get_data(self) -> MeteoluxData:
        """Get data from the API and parse it into a MeteoluxData object.

        Tries the new API first, falls back to CSV data if that fails.

        Raises:
            MeteoluxApiClientError: If the API returns an error or the data is malformed.
            MeteoluxApiConnectionError: If there is a connection error.
        """
        # Try the new API first
        try:
            return await self._async_get_api_data()
        except (MeteoluxApiClientError, MeteoluxApiConnectionError) as err:
            _LOGGER.warning("Failed to get data from new API, falling back to CSV: %s", err)
            
        # Fallback to CSV data
        return await self._async_get_csv_data()

    async def _async_get_api_data(self) -> MeteoluxData:
        """Get data from the new MeteoLux API."""
        try:
            async with self._session.get(WEATHER_ENDPOINT) as response:
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as err:
            if err.status == 404:
                # Try the metapp endpoint instead
                try:
                    async with self._session.get(METAPP_WEATHER_ENDPOINT) as response:
                        response.raise_for_status()
                        data = await response.json()
                except ClientResponseError as metapp_err:
                    raise MeteoluxApiClientError(f"Both API endpoints failed: {err.status}, {metapp_err.status}") from metapp_err
            else:
                raise MeteoluxApiClientError(f"HTTP error: {err.status}") from err
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            raise MeteoluxApiConnectionError("Could not connect to MeteoLux API") from err

        try:
            return MeteoluxData.from_api_response(data)
        except (KeyError, ValueError, TypeError) as err:
            raise MeteoluxApiClientError("Failed to parse MeteoLux API data") from err

    async def _async_get_csv_data(self) -> MeteoluxData:
        """Get data from the CSV data source (legacy)."""
        try:
            async with self._session.get(DATA_URL) as response:
                response.raise_for_status()
                data = await response.text()
        except ClientResponseError as err:
            raise MeteoluxApiClientError(f"HTTP error: {err.status}") from err
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            raise MeteoluxApiConnectionError("Could not connect to MeteoLux CSV") from err

        # The first line is "sep=;", skip it.
        data_io = io.StringIO(data)
        next(data_io, None)
        reader = csv.reader(data_io, delimiter=";")

        raw_data: dict[str, str] = {}
        for row in reader:
            if not row or len(row) < 2:
                continue
            key, value, *_ = row
            raw_data[key] = value.strip().replace("<br />", "")

        try:
            return MeteoluxData.from_raw(raw_data)
        except (csv.Error, KeyError, IndexError, ValueError, TypeError) as err:
            raise MeteoluxApiClientError("Failed to parse MeteoLux CSV data") from err
