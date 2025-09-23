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

from .const import API_URL, DATA_URL

_LOGGER = logging.getLogger(__name__)


@dataclass
class Forecast:
    """Class for holding forecast data."""

    weather: str | None
    icon: str | None
    temp_low: float | None
    temp_high: float | None
    precipitation: float | None
    wind_direction: str | None
    wind_force: float | None
    wind_gusts: float | None
    is_displayed: bool = True
    datetime: datetime | None = None


@dataclass
class MeteoluxData:
    """Class for holding MeteoLux data."""

    city: str | None
    created: datetime
    temp_min: float | None
    temp_max: float | None
    current_weather: Forecast | None
    forecasts: dict[str, Forecast]

    @classmethod
    def from_raw(cls, raw_data: dict[str, str]) -> Self:
        """Parse raw data from the CSV endpoint into a MeteoluxData object."""
        created_str = raw_data.get("created")
        if not created_str:
            raise ValueError("Missing 'created' timestamp")

        data = {
            "city": "Luxembourg",
            "created": datetime.strptime(created_str, "%d-%m-%Y %H:%M:%S"),
            "temp_min": _parse_float(raw_data.get("temp_min")),
            "temp_max": _parse_float(raw_data.get("temp_max")),
            "current_weather": None,
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
    def from_json(cls, data: dict[str, Any]) -> Self:
        """Parse JSON data into a MeteoluxData object."""
        current = data["forecast"]["current"]
        daily = data["forecast"]["daily"]

        forecasts = {}
        for day in daily:
            forecasts[day["date"]] = Forecast(
                datetime=datetime.fromisoformat(day["date"]),
                weather=day["icon"]["name"],
                icon=day["icon"]["name"],
                temp_low=_parse_float(day["temperatureMin"]["temperature"]),
                temp_high=_parse_float(day["temperatureMax"]["temperature"]),
                precipitation=None,
                wind_direction=day["wind"]["direction"],
                wind_force=_parse_float(day["wind"]["speed"]),
                wind_gusts=None,
            )

        return cls(
            city=data["city"]["name"],
            created=datetime.fromisoformat(current["date"]),
            temp_min=_parse_float(daily[0]["temperatureMin"]["temperature"]),
            temp_max=_parse_float(daily[0]["temperatureMax"]["temperature"]),
            current_weather=Forecast(
                datetime=datetime.fromisoformat(current["date"]),
                weather=current["icon"]["name"],
                icon=current["icon"]["name"],
                temp_low=None,
                temp_high=_parse_float(current["temperature"]["temperature"]),
                precipitation=_parse_float(current["rain"]),
                wind_direction=current["wind"]["direction"],
                wind_force=_parse_float(current["wind"]["speed"]),
                wind_gusts=None,
            ),
            forecasts=forecasts,
        )


class MeteoluxApiClientError(Exception):
    """Exception to indicate a general API error."""


class MeteoluxApiConnectionError(MeteoluxApiClientError):
    """Exception to indicate a connection error."""


def _parse_float(value: str | int | float | None, decimal_separator: str = ".") -> float | None:
    """Parse a float from a string, returning None on failure."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
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
    """MeteoLux API client for the JSON API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        lat: float | None = None,
        long: float | None = None,
    ):
        """Initialize the client."""
        self._session = session
        self._lat = lat
        self._long = long

    async def async_get_data(self) -> MeteoluxData:
        """Get data from the API and parse it into a MeteoluxData object."""
        params = {}
        if self._lat and self._long:
            params["lat"] = self._lat
            params["long"] = self._long

        _LOGGER.debug(f"Requesting weather data with params: {params}")

        try:
            async with self._session.get(
                f"{API_URL}/metapp/weather", params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except ClientResponseError as err:
            raise MeteoluxApiClientError(f"HTTP error: {err.status}") from err
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            raise MeteoluxApiConnectionError("Could not connect to MeteoLux") from err

        try:
            return MeteoluxData.from_json(data)
        except (KeyError, IndexError, ValueError, TypeError) as err:
            raise MeteoluxApiClientError("Failed to parse MeteoLux data") from err
