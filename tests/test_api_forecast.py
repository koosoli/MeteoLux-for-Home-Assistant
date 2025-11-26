"""Tests for the MeteoLux API client with forecast support."""
from __future__ import annotations

import pytest
from datetime import datetime

from custom_components.meteolux.api import MeteoluxData


@pytest.fixture
def api_response_data() -> dict[str, any]:
    """Return sample API response data."""
    return {
        "current": {
            "datetime": "2025-09-23T15:30:00+02:00",
            "temperature": 18.5,
            "humidity": 65,
            "pressure": 1015.2,
            "wind": {
                "speed": 12.3,
                "direction": "SW"
            },
            "visibility": 10000,
            "weather": {
                "description": "Partly cloudy"
            }
        },
        "daily": [
            {
                "datetime": "2025-09-23T00:00:00+02:00",
                "temperature": {
                    "max": 22.1,
                    "min": 12.8
                },
                "precipitation": 0.2,
                "wind": {
                    "speed": 15.5,
                    "direction": "W"
                },
                "humidity": 68,
                "pressure": 1014.8,
                "weather": {
                    "description": "Light rain"
                }
            },
            {
                "datetime": "2025-09-24T00:00:00+02:00",
                "temperature": {
                    "max": 19.3,
                    "min": 10.2
                },
                "precipitation": 2.5,
                "wind": {
                    "speed": 18.2,
                    "direction": "NW"
                },
                "humidity": 72,
                "pressure": 1012.3,
                "weather": {
                    "description": "Moderate rain"
                }
            }
        ],
        "hourly": [
            {
                "datetime": "2025-09-23T16:00:00+02:00",
                "temperature": 19.2,
                "precipitation": 0.1,
                "wind": {
                    "speed": 11.8,
                    "direction": "SW"
                },
                "humidity": 63,
                "pressure": 1015.5,
                "cloud_coverage": 45,
                "weather": {
                    "description": "Few clouds"
                }
            },
            {
                "datetime": "2025-09-23T17:00:00+02:00",
                "temperature": 18.9,
                "precipitation": 0.0,
                "wind": {
                    "speed": 10.2,
                    "direction": "W"
                },
                "humidity": 61,
                "pressure": 1015.8,
                "cloud_coverage": 30,
                "weather": {
                    "description": "Clear sky"
                }
            }
        ]
    }


def test_api_response_parsing(api_response_data: dict[str, any]) -> None:
    """Test parsing of API response data."""
    data = MeteoluxData.from_api_response(api_response_data, "test_endpoint")

    # Test current weather
    assert data.current_weather is not None
    assert data.current_weather.temperature == 18.5
    assert data.current_weather.humidity == 65
    assert data.current_weather.pressure == 1015.2
    assert data.current_weather.wind_speed == 12.3
    assert data.current_weather.wind_direction == "SW"
    assert data.current_weather.visibility == 10000
    assert data.current_weather.condition == "Partly cloudy"

    # Test daily forecasts
    assert data.daily_forecasts is not None
    assert len(data.daily_forecasts) == 2

    first_day = data.daily_forecasts[0]
    assert first_day.temperature_max == 22.1
    assert first_day.temperature_min == 12.8
    assert first_day.precipitation == 0.2
    assert first_day.wind_speed == 15.5
    assert first_day.wind_direction == "W"
    assert first_day.humidity == 68
    assert first_day.pressure == 1014.8
    assert first_day.condition == "Light rain"

    second_day = data.daily_forecasts[1]
    assert second_day.temperature_max == 19.3
    assert second_day.temperature_min == 10.2
    assert second_day.precipitation == 2.5

    # Test hourly forecasts
    assert data.hourly_forecasts is not None
    assert len(data.hourly_forecasts) == 2

    first_hour = data.hourly_forecasts[0]
    assert first_hour.temperature == 19.2
    assert first_hour.precipitation == 0.1
    assert first_hour.wind_speed == 11.8
    assert first_hour.wind_direction == "SW"
    assert first_hour.humidity == 63
    assert first_hour.pressure == 1015.5
    assert first_hour.cloud_coverage == 45
    assert first_hour.condition == "Few clouds"

    second_hour = data.hourly_forecasts[1]
    assert second_hour.temperature == 18.9
    assert second_hour.precipitation == 0.0
    assert second_hour.condition == "Clear sky"


def test_api_response_with_missing_data() -> None:
    """Test parsing of API response with missing data."""
    minimal_data = {
        "current": {
            "temperature": 15.0
        },
        "daily": [],
        "hourly": []
    }
    
    data = MeteoluxData.from_api_response(minimal_data, "test_endpoint")

    assert data.current_weather is not None
    assert data.current_weather.temperature == 15.0
    assert data.current_weather.humidity is None
    assert data.daily_forecasts == []
    assert data.hourly_forecasts == []


def test_api_response_empty() -> None:
    """Test parsing of empty API response."""
    empty_data = {}
    
    data = MeteoluxData.from_api_response(empty_data, "test_endpoint")

    assert data.current_weather is not None
    assert data.current_weather.temperature is None
    assert data.daily_forecasts == []
    assert data.hourly_forecasts == []
