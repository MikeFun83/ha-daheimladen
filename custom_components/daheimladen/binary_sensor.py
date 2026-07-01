from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .const import DOMAIN
from .entity import DaheimladenEntity

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([
        DaheimladenChargingBinarySensor(coordinator, entry),
        DaheimladenOnlineBinarySensor(coordinator, entry),
        DaheimladenConnectedBinarySensor(coordinator, entry),
    ])

class DaheimladenChargingBinarySensor(DaheimladenEntity, BinarySensorEntity):
    _attr_name = "Lädt"
    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "binary_charging")

    @property
    def is_on(self):
        return bool((self.coordinator.data or {}).get("is_charging"))

class DaheimladenOnlineBinarySensor(DaheimladenEntity, BinarySensorEntity):
    _attr_name = "Online"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:cloud-check"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "binary_online")

    @property
    def is_on(self):
        return bool((self.coordinator.data or {}).get("is_online"))

class DaheimladenConnectedBinarySensor(DaheimladenEntity, BinarySensorEntity):
    _attr_name = "Fahrzeug verbunden"
    _attr_device_class = BinarySensorDeviceClass.PLUG
    _attr_icon = "mdi:ev-plug-type2"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "binary_vehicle_connected")

    @property
    def is_on(self):
        return bool((self.coordinator.data or {}).get("is_connected"))
