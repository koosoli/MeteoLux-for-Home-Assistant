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
    wind_gusts: float | None
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
    wind_gusts: float | None
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
class Vigilance:
    """Class for holding vigilance data."""

    datetime_start: datetime | None
    datetime_end: datetime | None
    level: int | None
    type: int | None
    group: int | None
    region: str | None
    description: str | None


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
    vigilances: list[Vigilance] | None = None
    data_source: str | None = None
    api_endpoint_used: str | None = None

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
            "data_source": "CSV",
            "vigilances": None,
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
    def from_api_response(cls, api_data: dict[str, Any], endpoint_used: str) -> Self:
        """Parse API response data into a MeteoluxData object."""
        forecast_data = api_data.get("forecast", api_data)
        history_data = api_data.get("data", {}).get("history")
        now = datetime.now()

        created = now  # Default value for created timestamp
        current_weather = None

        # Try to get current weather from history first, as it's more reliable
        if history_data and isinstance(history_data, list):
            try:
                # Get the latest entry from history that is not in the future
                _LOGGER.debug(f"Now: {now}")
                valid_history = []
                for e in history_data:
                    if "date" in e:
                        try:
                            entry_dt = datetime.fromisoformat(str(e["date"]))
                            if entry_dt <= now:
                                valid_history.append(e)
                        except (ValueError, TypeError):
                            _LOGGER.warning(f"Could not parse history date: {e['date']}")

                _LOGGER.debug(f"Found {len(valid_history)} valid history entries.")

                if valid_history:
                    latest_history = max(valid_history, key=lambda x: x["date"])
                    _LOGGER.debug(f"Latest history entry: {latest_history}")
                    history_dt = datetime.fromisoformat(str(latest_history["date"]))

                    current_weather = CurrentWeather(
                        datetime=history_dt,
                        temperature=latest_history.get("meanTemp"),
                        condition=None,  # History does not provide condition
                        humidity=None,  # Or humidity
                        pressure=None,  # Or pressure
                        wind_speed=None,
                        wind_direction=None,
                        visibility=None,
                    )
                    created = history_dt
                    _LOGGER.debug("Using recent history entry for current weather.")
            except (ValueError, TypeError, IndexError):
                _LOGGER.warning(
                    "Could not parse current weather from history data.", exc_info=True
                )

        # If history didn't yield current weather, fall back to the 'current' object
        if not current_weather:
            _LOGGER.debug(
                "History data not available or stale, falling back to 'current' object."
            )
            current_data = forecast_data.get("current", {})
            if current_data:
                timestamp_str = current_data.get("datetime") or current_data.get("date")
                if timestamp_str:
                    try:
                        current_dt = datetime.fromisoformat(
                            str(timestamp_str).replace("Z", "+00:00")
                        )

                        # Validate that the data is not from the future
                        if current_dt > now + timedelta(hours=1):
                            _LOGGER.warning(
                                "API's 'current' weather data is from the future (%s), discarding it.",
                                current_dt,
                            )
                        else:
                            # Data is valid, parse it
                            weather_condition = None
                            if isinstance(current_data.get("weather"), dict):
                                weather_condition = (
                                    current_data["weather"].get("condition")
                                    or current_data["weather"].get("description")
                                )
                            elif isinstance(current_data.get("weather"), str):
                                weather_condition = current_data["weather"]
                            elif "condition" in current_data:
                                weather_condition = current_data["condition"]

                            if not weather_condition and isinstance(
                                current_data.get("icon"), dict
                            ):
                                weather_condition = current_data["icon"].get("name")

                            wind_speed = None
                            wind_direction = None
                            wind_data = current_data.get("wind", {})
                            if isinstance(wind_data, dict):
                                wind_speed = _parse_api_value(
                                    wind_data.get("speed")
                                    or wind_data.get("wind_speed")
                                )
                                wind_direction = wind_data.get(
                                    "direction"
                                ) or wind_data.get("wind_direction")

                            temp = current_data.get("temperature")
                            if isinstance(temp, dict):
                                temp = temp.get("temperature")

                            created = current_dt
                            current_weather = CurrentWeather(
                                datetime=created,
                                condition=weather_condition,
                                temperature=temp,
                                humidity=current_data.get("humidity"),
                                pressure=current_data.get("pressure")
                                or current_data.get("qnh"),
                                wind_speed=wind_speed,
                                wind_direction=wind_direction,
                                visibility=current_data.get("visibility"),
                            )

                    except (ValueError, TypeError):
                        _LOGGER.warning(
                            "Could not parse 'current' timestamp '%s'", timestamp_str
                        )

        # Parse daily forecasts
        daily_forecasts = []
        daily_data = forecast_data.get("daily", [])
        if daily_data:
            for day_data in daily_data:
                if not day_data:
                    continue
                
                # Handle datetime parsing
                day_datetime = created
                if "datetime" in day_data:
                    try:
                        day_datetime = datetime.fromisoformat(str(day_data["datetime"]).replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        day_datetime = created + timedelta(days=len(daily_forecasts))
                elif "date" in day_data:
                    try:
                        day_datetime = datetime.fromisoformat(str(day_data["date"]).replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        day_datetime = created + timedelta(days=len(daily_forecasts))
                
                # Extract weather condition
                weather_condition = None
                if isinstance(day_data.get("icon"), dict):
                    weather_condition = day_data["icon"].get("name")
                
                # Extract temperature data
                temp_max = day_data.get("temperatureMax")
                if isinstance(temp_max, dict):
                    temp_max = temp_max.get("temperature")
                
                temp_min = day_data.get("temperatureMin")
                if isinstance(temp_min, dict):
                    temp_min = temp_min.get("temperature")

                # Extract wind data
                wind_speed = None
                wind_direction = None
                wind_gusts = None
                wind_data = day_data.get("wind", {})
                if isinstance(wind_data, dict):
                    wind_speed = _parse_api_value(wind_data.get("speed"))
                    wind_direction = wind_data.get("direction")
                    wind_gusts = _parse_api_value(wind_data.get("gusts"))
                
                daily_forecasts.append(DailyForecast(
                    datetime=day_datetime,
                    condition=weather_condition,
                    temperature_max=temp_max,
                    temperature_min=temp_min,
                    precipitation=_parse_api_value(day_data.get("rain")),
                    wind_speed=wind_speed,
                    wind_direction=wind_direction,
                    wind_gusts=wind_gusts,
                    humidity=day_data.get("humidity"),
                    pressure=day_data.get("pressure") or day_data.get("qnh"),
                ))

        # Parse hourly forecasts
        hourly_forecasts = []
        hourly_data = forecast_data.get("hourly", [])
        if hourly_data:
            for hour_data in hourly_data:
                if not hour_data:
                    continue
                
                # Handle datetime parsing
                hour_datetime = created
                if "datetime" in hour_data:
                    try:
                        hour_datetime = datetime.fromisoformat(str(hour_data["datetime"]).replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        hour_datetime = created + timedelta(hours=len(hourly_forecasts))
                elif "date" in hour_data:
                    try:
                        hour_datetime = datetime.fromisoformat(str(hour_data["date"]).replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        hour_datetime = created + timedelta(hours=len(hourly_forecasts))
                
                # Extract weather condition
                weather_condition = None
                if isinstance(hour_data.get("icon"), dict):
                    weather_condition = hour_data["icon"].get("name")
                
                temp = hour_data.get("temperature")
                if isinstance(temp, dict):
                    temp = temp.get("temperature")
                if isinstance(temp, list):
                    try:
                        # Take the average of the range if it's a list
                        temp = sum(temp) / len(temp)
                    except (TypeError, ZeroDivisionError):
                        temp = None

                # Extract wind data
                wind_speed = None
                wind_direction = None
                wind_gusts = None
                wind_data = hour_data.get("wind", {})
                if isinstance(wind_data, dict):
                    wind_speed = _parse_api_value(wind_data.get("speed"))
                    wind_direction = wind_data.get("direction")
                    wind_gusts = _parse_api_value(wind_data.get("gusts"))
                
                hourly_forecasts.append(HourlyForecast(
                    datetime=hour_datetime,
                    condition=weather_condition,
                    temperature=temp,
                    precipitation=_parse_api_value(hour_data.get("rain")),
                    wind_speed=wind_speed,
                    wind_direction=wind_direction,
                    wind_gusts=wind_gusts,
                    humidity=hour_data.get("humidity"),
                    pressure=hour_data.get("pressure") or hour_data.get("qnh"),
                    cloud_coverage=hour_data.get("cloud_coverage") or hour_data.get("clouds"),
                ))

        # Parse vigilances
        vigilances = []
        vigilance_data = api_data.get("vigilances", [])
        if vigilance_data:
            for vigilance_item in vigilance_data:
                if not vigilance_item:
                    continue

                start_time = None
                if "datetimeStart" in vigilance_item:
                    try:
                        start_time = datetime.fromisoformat(
                            str(vigilance_item["datetimeStart"]).replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                end_time = None
                if "datetimeEnd" in vigilance_item:
                    try:
                        end_time = datetime.fromisoformat(
                            str(vigilance_item["datetimeEnd"]).replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass

                vigilances.append(
                    Vigilance(
                        datetime_start=start_time,
                        datetime_end=end_time,
                        level=vigilance_item.get("level"),
                        type=vigilance_item.get("type"),
                        group=vigilance_item.get("group"),
                        region=vigilance_item.get("region"),
                        description=vigilance_item.get("description"),
                    )
                )

        # Determine temperature range from daily forecasts if available
        temp_min = None
        temp_max = None
        if daily_forecasts:
            temps_min = [f.temperature_min for f in daily_forecasts if f.temperature_min is not None]
            temps_max = [f.temperature_max for f in daily_forecasts if f.temperature_max is not None]
            if temps_min:
                temp_min = min(temps_min)
            if temps_max:
                temp_max = max(temps_max)
        elif current_weather and current_weather.temperature is not None:
            temp_min = temp_max = current_weather.temperature

        return cls(
            created=created,
            temp_min=temp_min,
            temp_max=temp_max,
            forecasts={},  # Keep legacy format for compatibility
            current_weather=current_weather,
            daily_forecasts=daily_forecasts,
            hourly_forecasts=hourly_forecasts,
            vigilances=vigilances,
            data_source="API",
            api_endpoint_used=endpoint_used,
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


def _parse_float_from_string(value: str | None) -> float | None:
    """Parse a float from a string like '12.3 mm'."""
    if value is None:
        return None
    try:
        return float(value.split(" ")[0].replace(",", "."))
    except (ValueError, TypeError):
        return None


def _parse_api_value(value: str | None) -> float | None:
    """Parse a value from the API, which can be a single number or a range."""
    if value is None or value == "":
        return None

    # Treat value as a string to be safe
    str_value = str(value)

    # First, try to parse it as a simple float
    try:
        return float(str_value.split(" ")[0].replace(",", "."))
    except (ValueError, TypeError):
        # If that fails, it might be a range (e.g., "5-10")
        try:
            cleaned_value = str_value.split(" ")[0]
            _, high = _parse_range(cleaned_value)
            return high
        except (ValueError, TypeError, IndexError):
            _LOGGER.warning("Could not parse value: %s", value)
            return None


def _parse_precipitation(value: str | None) -> float | None:
    """Parse precipitation string (e.g., '7-9 l/m²') and return the higher value in mm."""
    return _parse_float_from_string(value)


def _parse_wind_force(value: str | None) -> float | None:
    """Parse wind force string (e.g., '05-10 km/h') and return the higher value."""
    if value is None:
        return None
    cleaned_value = value.split(" ")[0]
    _, high = _parse_range(cleaned_value)
    return high


class MeteoluxApiClient:
    """MeteoLux API client."""

    def __init__(self, session: aiohttp.ClientSession, latitude: float, longitude: float):
        """Initialize the client."""
        self._session = session
        self._latitude = latitude
        self._longitude = longitude

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
        data = None
        endpoint_used = None
        params = {"lat": self._latitude, "long": self._longitude, "langcode": "en"}
        headers = {
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        
        # Prioritize METAPP_WEATHER_ENDPOINT as it seems more stable
        try:
            async with self._session.get(
                METAPP_WEATHER_ENDPOINT, params=params, headers=headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                endpoint_used = METAPP_WEATHER_ENDPOINT
        except ClientResponseError as err:
            if err.status == 404:
                _LOGGER.warning(
                    "METAPP endpoint not found, falling back to WEATHER endpoint."
                )
                # Try the main weather endpoint instead
                try:
                    async with self._session.get(
                        WEATHER_ENDPOINT, params=params, headers=headers
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()
                        endpoint_used = WEATHER_ENDPOINT
                except ClientResponseError as weather_err:
                    raise MeteoluxApiClientError(
                        f"Both API endpoints failed: {err.status}, {weather_err.status}"
                    ) from weather_err
            else:
                raise MeteoluxApiClientError(f"HTTP error: {err.status}") from err
        except (ClientConnectorError, asyncio.TimeoutError) as err:
            raise MeteoluxApiConnectionError("Could not connect to MeteoLux API") from err

        try:
            _LOGGER.debug(f"Successfully fetched data from {endpoint_used}")
            _LOGGER.debug(f"API response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            # Log structure for debugging
            if isinstance(data, dict):
                if "current" in data:
                    _LOGGER.debug(f"Current weather keys: {list(data['current'].keys()) if isinstance(data['current'], dict) else 'Not a dict'}")
                if "hourly" in data:
                    _LOGGER.debug(f"Hourly forecast count: {len(data['hourly']) if isinstance(data['hourly'], list) else 'Not a list'}")
                if "daily" in data:
                    _LOGGER.debug(f"Daily forecast count: {len(data['daily']) if isinstance(data['daily'], list) else 'Not a list'}")
            
            return MeteoluxData.from_api_response(data, endpoint_used)
        except (KeyError, ValueError, TypeError) as err:
            _LOGGER.error(f"Failed to parse MeteoLux API data from {endpoint_used}: {err}")
            _LOGGER.error(f"Raw data structure: {data}")
            raise MeteoluxApiClientError(f"Failed to parse MeteoLux API data: {err}") from err

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
