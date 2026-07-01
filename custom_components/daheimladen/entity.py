from __future__ import annotations

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN

class DaheimladenEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, suffix: str) -> None:
        super().__init__(coordinator)
        self.entry = entry
        self.station_id = entry.data["station_id"]
        self._attr_unique_id = f"{self.station_id}_{suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        data = self.coordinator.data or {}
        return DeviceInfo(
            identifiers={(DOMAIN, self.station_id)},
            name=f"DaheimLaden {self.station_id}",
            manufacturer=data.get("manufacturer") or "DaheimLaden / WEEYU",
            model=data.get("model") or "SingleSocketCharger",
            configuration_url="https://daheimladen.com/dashboard",
        )
