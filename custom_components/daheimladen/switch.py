from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from .const import DOMAIN
from .entity import DaheimladenEntity

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DaheimladenChargingSwitch(data["coordinator"], data["api"], entry)])

class DaheimladenChargingSwitch(DaheimladenEntity, SwitchEntity):
    _attr_name = "Laden"
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, api, entry):
        super().__init__(coordinator, entry, "switch_charging")
        self.api = api

    @property
    def is_on(self):
        return bool((self.coordinator.data or {}).get("is_charging"))

    async def async_turn_on(self, **kwargs):
        await self.api.remote_start()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.api.remote_stop()
        await self.coordinator.async_request_refresh()
