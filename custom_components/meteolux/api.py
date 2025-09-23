"""API client for MeteoLux."""
from __future__ import annotations

import asyncio
import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Self

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError, ClientResponseError

from .const import DATA_URL

_LOGGER = logging.getLogger(__name__)


@dataclass
class MeteoluxData:
    """Class for holding MeteoLux data."""

    created: datetime
    temp_min: float | None
    temp_max: float | None
    forecasts: dict[str, Forecast]
    city: str | None = None
    current_weather: Forecast | None = None

    @classmethod
    def from_raw(cls, raw_data: dict[str, str]) -> Self:
        """Parse raw data into a MeteoluxData object."""
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
    def from_json(cls, json_data: dict[str, Any]) -> Self:
        """Parse JSON data into a MeteoluxData object."""
        # Extract city information
        city_name = json_data.get("city", {}).get("name", "Luxembourg")
        
        # Get forecast data
        forecast_data = json_data.get("forecast", {})
        
        # Extract current weather if available
        current_weather = None
        current_data = forecast_data.get("current")
        if current_data:
            current_weather = Forecast(
                is_displayed=True,
                weather=current_data.get("icon", {}).get("name"),
                icon=str(current_data.get("icon", {}).get("id", "")),
                temp_range=None,
                temp_low=None,
                temp_high=_parse_float(str(current_data.get("temperature", {}).get("temperature", ""))),
                precipitation=_parse_float(str(current_data.get("rain", "0"))),
                wind_direction=current_data.get("wind", {}).get("direction"),
                wind_force=_parse_float(str(current_data.get("wind", {}).get("speed", "0"))),
                wind_gusts=None,
                rain=_parse_float(str(current_data.get("rain", "0"))),
                snow=_parse_float(str(current_data.get("snow", "0"))),
            )
        
        # Parse daily forecasts
        forecasts = {}
        daily_data = forecast_data.get("daily", [])
        
        # Find min/max temperatures from daily forecasts
        temp_min = None
        temp_max = None
        
        for daily in daily_data:
            date_str = daily.get("date", "")
            
            # Extract temperatures
            temp_min_val = _parse_float(str(daily.get("temperatureMin", {}).get("temperature", "")))
            temp_max_val = _parse_float(str(daily.get("temperatureMax", {}).get("temperature", "")))
            
            # Update overall min/max
            if temp_min_val is not None:
                temp_min = temp_min_val if temp_min is None else min(temp_min, temp_min_val)
            if temp_max_val is not None:
                temp_max = temp_max_val if temp_max is None else max(temp_max, temp_max_val)
            
            forecasts[date_str] = Forecast(
                is_displayed=True,
                weather=daily.get("icon", {}).get("name"),
                icon=str(daily.get("icon", {}).get("id", "")),
                temp_range=None,
                temp_low=temp_min_val,
                temp_high=temp_max_val,
                precipitation=_parse_float(str(daily.get("rain", "0"))),
                wind_direction=daily.get("wind", {}).get("direction"),
                wind_force=_parse_float(str(daily.get("wind", {}).get("speed", "0"))),
                wind_gusts=None,
                sunshine=_parse_float(str(daily.get("sunshine", ""))),
                uv_index=_parse_float(str(daily.get("uvIndex", ""))),
                rain=_parse_float(str(daily.get("rain", "0"))),
                snow=_parse_float(str(daily.get("snow", "0"))),
            )
        
        # Use current timestamp if no specific timestamp is provided
        created = datetime.now()
        if current_data and current_data.get("date"):
            try:
                created = datetime.fromisoformat(current_data["date"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass
        
        return cls(
            created=created,
            temp_min=temp_min,
            temp_max=temp_max,
            forecasts=forecasts,
            city=city_name,
            current_weather=current_weather,
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
    sunshine: float | None = None
    uv_index: float | None = None
    rain: float | None = None
    snow: float | None = None


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

        Raises:
            MeteoluxApiClientError: If the API returns an error or the data is malformed.
            MeteoluxApiConnectionError: If there is a connection error.
        """
        try:
            async with self._session.get(DATA_URL) as response:
                response.raise_for_status()
                data = await response.text()
        except ClientResponseError as err:
            raise MeteoluxApiClientError(f"HTTP error: {err.status}") from err
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            raise MeteoluxApiConnectionError("Could not connect to MeteoLux") from err

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
            raise MeteoluxApiClientError("Failed to parse MeteoLux data") from err


class MeteoluxApiJsonClient:
    """MeteoLux JSON API client."""

    def __init__(self, session: aiohttp.ClientSession, latitude: float, longitude: float):
        """Initialize the client."""
        self._session = session
        self._latitude = latitude
        self._longitude = longitude

    async def async_get_data(self) -> MeteoluxData:
        """Get data from the JSON API and parse it into a MeteoluxData object.

        Raises:
            MeteoluxApiClientError: If the API returns an error or the data is malformed.
            MeteoluxApiConnectionError: If there is a connection error.
        """
        from .const import API_URL

        # Construct the API URL with location parameters
        url = f"{API_URL}/forecast"
        params = {
            "lat": self._latitude,
            "lon": self._longitude,
        }

        try:
            async with self._session.get(url, params=params) as response:
                response.raise_for_status()
                json_data = await response.json()
        except ClientResponseError as err:
            raise MeteoluxApiClientError(f"HTTP error: {err.status}") from err
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            raise MeteoluxApiConnectionError("Could not connect to MeteoLux JSON API") from err

        try:
            return MeteoluxData.from_json(json_data)
        except (KeyError, IndexError, ValueError, TypeError) as err:
            raise MeteoluxApiClientError("Failed to parse MeteoLux JSON data") from err
