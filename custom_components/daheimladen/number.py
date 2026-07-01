from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberDeviceClass
from homeassistant.const import UnitOfElectricCurrent
from .const import DEFAULT_CHARGE_RATE, DOMAIN
from .entity import DaheimladenEntity

async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([DaheimladenChargeRateNumber(data["coordinator"], data["api"], entry)])

class DaheimladenChargeRateNumber(DaheimladenEntity, NumberEntity):
    _attr_name = "Ladestrom"
    _attr_icon = "mdi:current-ac"
    _attr_native_min_value = 6
    _attr_native_max_value = 16
    _attr_native_step = 1
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_device_class = NumberDeviceClass.CURRENT

    def __init__(self, coordinator, api, entry):
        super().__init__(coordinator, entry, "number_charge_rate")
        self.api = api
        self._local_value = None

    @property
    def native_value(self):
        value = (self.coordinator.data or {}).get("charge_rate")
        if value is not None:
            return value
        if self._local_value is not None:
            return self._local_value
        return getattr(self.api, "last_charge_rate", None) or DEFAULT_CHARGE_RATE

    async def async_set_native_value(self, value: float):
        ampere = int(round(value))
        await self.api.set_charge_rate(ampere)
        self._local_value = ampere
        await self.coordinator.async_request_refresh()
