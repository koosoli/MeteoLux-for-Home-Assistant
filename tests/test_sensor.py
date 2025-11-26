"""Tests for the MeteoLux sensor platform."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from custom_components.meteolux.api import MeteoluxData, Vigilance
from custom_components.meteolux.sensor import (
    _get_vigilance_level,
    _get_vigilance_attributes,
)


def test_get_vigilance_level_with_expired_warning() -> None:
    """Test that expired vigilance warnings are ignored."""
    now = datetime.now(timezone.utc)
    expired_warning = Vigilance(
        datetime_start=now - timedelta(hours=2),
        datetime_end=now - timedelta(hours=1),
        level=3,
        type=5,
        group=1,
        region="all",
        description="Expired Warning",
    )
    data = MeteoluxData(
        created=now,
        temp_min=None,
        temp_max=None,
        forecasts={},
        vigilances=[expired_warning],
    )

    assert _get_vigilance_level(data) == "none"


def test_get_vigilance_attributes_with_expired_warning() -> None:
    """Test that attributes are empty when warnings are expired."""
    now = datetime.now(timezone.utc)
    expired_warning = Vigilance(
        datetime_start=now - timedelta(hours=2),
        datetime_end=now - timedelta(hours=1),
        level=3,
        type=5,
        group=1,
        region="all",
        description="Expired Warning",
    )
    data = MeteoluxData(
        created=now,
        temp_min=None,
        temp_max=None,
        forecasts={},
        vigilances=[expired_warning],
    )

    assert _get_vigilance_attributes(data) == {}
