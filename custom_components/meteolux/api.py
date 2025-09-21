import asyncio
import csv
import io
import logging
from datetime import datetime

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError

from .const import DATA_URL

_LOGGER = logging.getLogger(__name__)


def _parse_float(value: str | None, decimal_separator: str = ".") -> float | None:
    """Parse a float from a string, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value.replace(decimal_separator, "."))
    except (ValueError, TypeError):
        return None


def _parse_range(value: str | None) -> float | None:
    """Parse a range string (e.g., '5-10') and return the higher value."""
    if value is None:
        return None
    parts = value.replace(",", ".").strip().split("-")
    if len(parts) > 1:
        # "5-10" -> 10
        return _parse_float(parts[-1])
    # "5" -> 5
    return _parse_float(parts[0])


def _parse_precipitation(value: str | None) -> float | None:
    """Parse precipitation string (e.g., '7-9 l/m²') and return the higher value in mm."""
    if value is None:
        return None
    # "7-9 l/m²" -> "7-9"
    cleaned_value = value.split(" ")[0]
    return _parse_range(cleaned_value)


def _parse_wind_force(value: str | None) -> float | None:
    """Parse wind force string (e.g., '05-10 km/h') and return the higher value."""
    if value is None:
        return None
    # "05-10 km/h" -> "05-10"
    cleaned_value = value.split(" ")[0]
    return _parse_range(cleaned_value)


class MeteoluxApiClient:
    """MeteoLux API client."""

    def __init__(self, session: aiohttp.ClientSession):
        """Initialize the client."""
        self._session = session

    async def async_get_data(self) -> dict | None:
        """Get data from the API."""
        try:
            async with self._session.get(DATA_URL) as response:
                response.raise_for_status()
                data = await response.text()
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            _LOGGER.warning("Could not connect to MeteoLux", exc_info=err)
            return None

        # The first line is "sep=;", skip it.
        data_io = io.StringIO(data)
        next(data_io, None)
        reader = csv.reader(data_io, delimiter=";")

        raw_data = {}
        for row in reader:
            if not row or len(row) < 2:
                continue
            key, value, *_ = row
            raw_data[key] = value.strip()

        try:
            structured_data = {
                "created": datetime.strptime(
                    raw_data.get("created"), "%d-%m-%Y %H:%M:%S"
                ),
                "day": {
                    "temp_min": _parse_float(raw_data.get("temp_min")),
                    "temp_max": _parse_float(raw_data.get("temp_max")),
                },
                "forecasts": {},
            }

            for i in range(1, 4):  # For morning, afternoon, evening
                prefix = f"{i}_"
                if f"{prefix}is_displayed" not in raw_data:
                    continue

                title = raw_data.get(f"{prefix}title", "").lower()
                if not title:
                    continue

                structured_data["forecasts"][title] = {
                    "is_displayed": raw_data.get(f"{prefix}is_displayed") == "1",
                    "weather": raw_data.get(f"{prefix}weather"),
                    "icon": raw_data.get(f"{prefix}icon"),
                    "temp_range": raw_data.get(f"{prefix}temp_range"),
                    "precipitation": _parse_precipitation(
                        raw_data.get(f"{prefix}precipitation")
                    ),
                    "wind_direction": raw_data.get(f"{prefix}wind_direction_tooltip"),
                    "wind_force": _parse_wind_force(raw_data.get(f"{prefix}wind_force")),
                    "wind_gusts": _parse_wind_force(raw_data.get(f"{prefix}wind_gusts")),
                }
            return structured_data

        except (csv.Error, KeyError, IndexError, ValueError, TypeError) as err:
            _LOGGER.error("Failed to parse MeteoLux data: %s", err)
            return None
