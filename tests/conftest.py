"""Fixtures for the MeteoLux tests."""
import pytest
from homeassistant.config_entries import ConfigEntry
from unittest.mock import MagicMock

from custom_components.meteolux.const import DOMAIN


@pytest.fixture
def config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    return MagicMock(spec=ConfigEntry, data={}, entry_id="test")
