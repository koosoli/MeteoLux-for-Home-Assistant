import asyncio
import csv
import io
import logging

import aiohttp
from aiohttp.client_exceptions import ClientConnectorError

_LOGGER = logging.getLogger(__name__)

DATA_URL = "https://data.public.lu/en/datasets/r/c05ecc27-aa44-4c96-bece-6149783e1758"

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

        reader = csv.reader(io.StringIO(data), delimiter=";")

        parsed_data = {}
        try:
            for row in reader:
                if not row or len(row) < 2:
                    continue
                key = row[0]
                value = row[1]
                parsed_data[key] = value

            # Structure the data
            structured_data = {
                "day": {
                    "temp_min": int(parsed_data.get("temp_min")),
                    "temp_max": int(parsed_data.get("temp_max")),
                },
                "forecasts": {}
            }

            for i in range(1, 4):
                prefix = f"{i}_"
                if f"{prefix}is_displayed" in parsed_data:
                    title = parsed_data.get(f"{prefix}title", "").lower()
                    if title:
                        structured_data["forecasts"][title] = {
                            "is_displayed": parsed_data.get(f"{prefix}is_displayed") == "1",
                            "weather": parsed_data.get(f"{prefix}weather"),
                            "icon": parsed_data.get(f"{prefix}icon"),
                            "temp_range": parsed_data.get(f"{prefix}temp_range"),
                            "precipitation": parsed_data.get(f"{prefix}precipitation", "").replace("<br />", "").strip(),
                            "wind_direction": parsed_data.get(f"{prefix}wind_direction_tooltip"),
                            "wind_force": parsed_data.get(f"{prefix}wind_force"),
                            "wind_gusts": parsed_data.get(f"{prefix}wind_gusts"),
                        }
            return structured_data

        except (csv.Error, KeyError, IndexError, ValueError) as err:
            _LOGGER.error("Failed to parse MeteoLux data: %s", err)
            return None
