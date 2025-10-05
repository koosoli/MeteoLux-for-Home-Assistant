"""Tests for the MeteoLux API client."""
from __future__ import annotations

import pytest

from custom_components.meteolux.api import MeteoluxData


@pytest.fixture
def raw_data() -> dict[str, str]:
    """Return raw data from the MeteoLux API."""
    return {
        "created": "21-09-2025 13:45:00",
        "temp_min": "12",
        "temp_max": "16",
        "1_is_displayed": "1",
        "1_title": "Morning",
        "1_weather": "Moderate rain",
        "1_icon": "22",
        "1_temp_range": "15 to 17",
        "1_precipitation": "7-9 l/m²",
        "1_wind_direction_tooltip": "South-West",
        "1_wind_force": "05-10 km/h",
        "1_wind_gusts": "20-30 km/h",
        "2_is_displayed": "1",
        "2_title": "Afternoon",
        "2_weather": "Overcast",
        "2_icon": "05",
        "2_temp_range": "12 to 14",
        "2_precipitation": "3-5 l/m²",
        "2_wind_direction_tooltip": "North-West",
        "2_wind_force": "05-10 km/h",
        "2_wind_gusts": "",
        "3_is_displayed": "0",
        "3_title": "Evening",
        "3_weather": "Clear sky",
        "3_icon": "01",
        "3_temp_range": "11 to 13",
        "3_precipitation": "0-1 l/m²",
        "3_wind_direction_tooltip": "North-West",
        "3_wind_force": "05-10 km/h",
        "3_wind_gusts": " ",
    }


def test_parsing(raw_data: dict[str, str]) -> None:
    """Test parsing of MeteoLux data."""
    data = MeteoluxData.from_raw(raw_data)

    assert data.temp_min == 12.0
    assert data.temp_max == 16.0
    assert len(data.forecasts) == 3

    morning = data.forecasts["morning"]
    assert morning.is_displayed is True
    assert morning.weather == "Moderate rain"
    assert morning.icon == "22"
    assert morning.temp_low == 15.0
    assert morning.temp_high == 17.0
    # assert morning.precipitation == 9.0
    assert morning.wind_direction == "South-West"
    assert morning.wind_force == 10.0
    assert morning.wind_gusts == 30.0

    afternoon = data.forecasts["afternoon"]
    assert afternoon.is_displayed is True
    assert afternoon.weather == "Overcast"
    assert afternoon.icon == "05"
    assert afternoon.temp_low == 12.0
    assert afternoon.temp_high == 14.0
    # assert afternoon.precipitation == 5.0
    assert afternoon.wind_direction == "North-West"
    assert afternoon.wind_force == 10.0
    assert afternoon.wind_gusts is None

    evening = data.forecasts["evening"]
    assert evening.is_displayed is False
    assert evening.weather == "Clear sky"
    assert evening.icon == "01"
    assert evening.temp_low == 11.0
    assert evening.temp_high == 13.0
    # assert evening.precipitation == 1.0
    assert evening.wind_direction == "North-West"
    assert evening.wind_force == 10.0
    assert evening.wind_gusts is None
