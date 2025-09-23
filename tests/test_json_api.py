"""Tests for the MeteoLux JSON API client."""
from __future__ import annotations

import pytest

from custom_components.meteolux.api import MeteoluxData


@pytest.fixture
def json_data() -> dict:
    """Return raw data from the MeteoLux JSON API."""
    return {
        "city": {"name": "Luxembourg"},
        "forecast": {
            "current": {
                "date": "2025-09-22T14:00:00+02:00",
                "icon": {"id": 1, "name": "sunny"},
                "wind": {"direction": "NW", "speed": "10"},
                "rain": "0",
                "snow": "0",
                "temperature": {"temperature": 15},
            },
            "hourly": [
                {
                    "date": "2025-09-22T15:00:00+02:00",
                    "icon": {"id": 2, "name": "partlycloudy"},
                    "wind": {"direction": "NW", "speed": "12"},
                    "rain": "0.1",
                    "snow": "0",
                    "temperature": {"temperature": 14},
                }
            ],
            "daily": [
                {
                    "date": "2025-09-23T00:00:00+02:00",
                    "icon": {"id": 3, "name": "rainy"},
                    "wind": {"direction": "W", "speed": "15"},
                    "rain": "5",
                    "snow": "0",
                    "temperatureMin": {"temperature": 8},
                    "temperatureMax": {"temperature": 16},
                    "sunshine": 4,
                    "uvIndex": 3,
                }
            ],
        },
    }


def test_parsing_json(json_data: dict) -> None:
    """Test parsing of MeteoLux JSON data."""
    data = MeteoluxData.from_json(json_data)

    assert data.city == "Luxembourg"
    assert data.temp_min == 8.0
    assert data.temp_max == 16.0
    assert len(data.forecasts) == 1

    current = data.current_weather
    assert current.temp_high == 15.0
    assert current.wind_force == 10.0
    assert current.wind_direction == "NW"
    assert current.weather == "sunny"

    daily = data.forecasts["2025-09-23T00:00:00+02:00"]
    assert daily.temp_low == 8.0
    assert daily.temp_high == 16.0
    assert daily.weather == "rainy"
    assert daily.wind_direction == "W"
    assert daily.wind_force == 15.0
