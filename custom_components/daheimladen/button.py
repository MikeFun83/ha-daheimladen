from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import EntityCategory
from .const import DOMAIN
from .entity import DaheimladenEntity

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        DaheimladenRefreshButton(data["coordinator"], entry),
        DaheimladenStartButton(data["coordinator"], data["api"], entry),
        DaheimladenStopButton(data["coordinator"], data["api"], entry),
        DaheimladenDiscoverIdtagButton(data["coordinator"], data["api"], entry),
    ])

class DaheimladenRefreshButton(DaheimladenEntity, ButtonEntity):
    _attr_name = "Aktualisieren"
    _attr_icon = "mdi:refresh"
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "button_refresh")
    async def async_press(self):
        await self.coordinator.async_request_refresh()

class DaheimladenStartButton(DaheimladenEntity, ButtonEntity):
    _attr_name = "Laden starten"
    _attr_icon = "mdi:play-circle"
    def __init__(self, coordinator, api, entry):
        super().__init__(coordinator, entry, "button_start")
        self.api = api
    async def async_press(self):
        await self.api.remote_start()
        await self.coordinator.async_request_refresh()

class DaheimladenStopButton(DaheimladenEntity, ButtonEntity):
    _attr_name = "Laden stoppen"
    _attr_icon = "mdi:stop-circle"
    def __init__(self, coordinator, api, entry):
        super().__init__(coordinator, entry, "button_stop")
        self.api = api
    async def async_press(self):
        await self.api.remote_stop()
        await self.coordinator.async_request_refresh()

class DaheimladenDiscoverIdtagButton(DaheimladenEntity, ButtonEntity):
    _attr_name = "IDTag suchen"
    _attr_icon = "mdi:card-search-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, api, entry):
        super().__init__(coordinator, entry, "button_discover_idtag")
        self.api = api

    async def async_press(self):
        await self.api.discover_idtag(force=True)
        await self.coordinator.async_request_refresh()
