"""Data update coordinator for the MeteoLux integration."""
from datetime import timedelta
import logging
from typing import Union

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    MeteoluxApiClient,
    MeteoluxApiClientError,
    MeteoluxData,
    MeteoluxApiJsonClient,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class MeteoluxDataUpdateCoordinator(DataUpdateCoordinator[MeteoluxData]):
    """MeteoLux data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, client: Union[MeteoluxApiClient, MeteoluxApiJsonClient]
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            # The data is updated daily, but we can poll more often to catch updates.
            # A 30 minute interval should be fine.
            update_interval=timedelta(minutes=30),
        )
        self.client = client

    async def _async_update_data(self) -> MeteoluxData:
        """Fetch data from API."""
        try:
            return await self.client.async_get_data()
        except MeteoluxApiClientError as err:
            raise UpdateFailed(str(err)) from err
