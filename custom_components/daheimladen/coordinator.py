from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class DaheimladenCoordinator(DataUpdateCoordinator):
    """Coordinator with adaptive polling.

    The DaheimLaden portal polls very frequently while a transaction is active.
    We keep standby polling moderate and switch to fast updates while charging.
    """

    def __init__(self, hass: HomeAssistant, api, name: str, standby_interval: int, fast_interval: int = 5, offline_interval: int = 60) -> None:
        self.api = api
        self.standby_interval = max(10, int(standby_interval or 30))
        self.fast_interval = max(5, int(fast_interval or 5))
        self.offline_interval = max(30, int(offline_interval or 60))
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_method=api.async_update,
            update_interval=timedelta(seconds=self.standby_interval),
        )

    async def _async_update_data(self):
        data = await self.update_method()
        if data.get("is_charging"):
            self.update_interval = timedelta(seconds=self.fast_interval)
        elif data.get("is_online") is False:
            self.update_interval = timedelta(seconds=self.offline_interval)
        else:
            self.update_interval = timedelta(seconds=self.standby_interval)
        return data
