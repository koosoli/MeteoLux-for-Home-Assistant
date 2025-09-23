"""Tests for the MeteoLux weather platform."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from custom_components.meteolux.const import DOMAIN
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
    }


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
            "daily": [
                {
                    "date": "2025-09-23T00:00:00+02:00",
                    "icon": {"id": 3, "name": "rainy"},
                    "wind": {"direction": "W", "speed": "15"},
                    "rain": "5",
                    "snow": "0",
                    "temperatureMin": {"temperature": 8},
                    "temperatureMax": {"temperature": 16},
                }
            ],
        },
    }


async def test_legacy_weather(
    hass: HomeAssistant, raw_data: dict, config_entry: ConfigEntry
) -> None:
    """Test the weather entity with the legacy API."""
    with patch(
        "custom_components.meteolux.api.MeteoluxApiClient.async_get_data",
        return_value=MeteoluxData.from_raw(raw_data),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("weather.meteolux_luxembourg")
        assert state.state == "rainy"
        assert state.attributes["temperature"] == 16.0


async def test_json_weather(
    hass: HomeAssistant, json_data: dict, config_entry: ConfigEntry
) -> None:
    """Test the weather entity with the JSON API."""
    config_entry.data = {
        "data_source": "JSON API",
        "latitude": 49.6116,
        "longitude": 6.1319,
    }
    with patch(
        "custom_components.meteolux.api.MeteoluxApiJsonClient.async_get_data",
        return_value=MeteoluxData.from_json(json_data),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("weather.meteolux_luxembourg")
        assert state.state == "sunny"
        assert state.attributes["temperature"] == 15.0
