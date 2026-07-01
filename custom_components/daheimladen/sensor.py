from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import (
    UnitOfPower,
    UnitOfEnergy,
    UnitOfTime,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfTemperature,
)

from .const import DOMAIN
from .entity import DaheimladenEntity

SENSORS = [
    ("status", "Status", None, None, None, "mdi:ev-station"),
    ("api_status", "API Status", None, None, None, "mdi:code-tags"),
    ("transaction_id", "Transaction ID", None, None, None, "mdi:identifier"),
    ("power_kw", "Ladeleistung", SensorDeviceClass.POWER, UnitOfPower.KILO_WATT, SensorStateClass.MEASUREMENT, "mdi:lightning-bolt"),
    ("energy_kwh", "Geladene Energie aktuelle Ladung", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL, "mdi:battery-charging"),
    ("meter_value_kwh", "Zählerstand", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING, "mdi:counter"),
    ("current", "Aktueller Strom Durchschnitt", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, "mdi:current-ac"),
    ("current_l1", "Strom L1", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, "mdi:current-ac"),
    ("current_l2", "Strom L2", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, "mdi:current-ac"),
    ("current_l3", "Strom L3", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, "mdi:current-ac"),
    ("voltage", "Spannung Durchschnitt", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, "mdi:sine-wave"),
    ("voltage_l1", "Spannung L1-L2", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, "mdi:sine-wave"),
    ("voltage_l2", "Spannung L2-L3", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, "mdi:sine-wave"),
    ("voltage_l3", "Spannung L3-L1", SensorDeviceClass.VOLTAGE, UnitOfElectricPotential.VOLT, SensorStateClass.MEASUREMENT, "mdi:sine-wave"),
    ("temperature", "Wallbox Temperatur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, "mdi:thermometer"),
    ("duration_seconds", "Ladezeit", SensorDeviceClass.DURATION, UnitOfTime.SECONDS, SensorStateClass.MEASUREMENT, "mdi:timer-outline"),
    ("charge_rate", "Eingestellter Ladestrom", SensorDeviceClass.CURRENT, UnitOfElectricCurrent.AMPERE, SensorStateClass.MEASUREMENT, "mdi:tune"),
    ("max_power_kw", "Maximale Ladeleistung", SensorDeviceClass.POWER, UnitOfPower.KILO_WATT, SensorStateClass.MEASUREMENT, "mdi:lightning-bolt-circle"),
    ("phases", "Phasen", None, None, None, "mdi:sine-wave"),
    ("manufacturer", "Hersteller", None, None, None, "mdi:factory"),
    ("model", "Modell", None, None, None, "mdi:ev-plug-type2"),
    ("current_time", "Status Zeit", SensorDeviceClass.TIMESTAMP, None, None, "mdi:clock-outline"),
    ("transaction_start_at", "Transaktion gestartet um", SensorDeviceClass.TIMESTAMP, None, None, "mdi:clock-start"),
    ("last_update", "Letzte Aktualisierung", SensorDeviceClass.TIMESTAMP, None, None, "mdi:update"),
    ("token_expires_at", "Token gültig bis", SensorDeviceClass.TIMESTAMP, None, None, "mdi:lock-clock"),
    ("idtag_status", "IDTag Status", None, None, None, "mdi:card-account-details-outline"),
    ("idtag_source", "IDTag Quelle", None, None, None, "mdi:source-branch"),
    ("idtag_discovery", "IDTag Suche Rohdaten", None, None, None, "mdi:card-search-outline"),
    ("raw_station", "Rohdaten Ladestation", None, None, None, "mdi:code-json"),
    ("raw_transaction", "Rohdaten aktive Ladung", None, None, None, "mdi:code-json"),
    ("raw_status", "Rohdaten Status", None, None, None, "mdi:code-json"),
]

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([DaheimladenSensor(coordinator, entry, *desc) for desc in SENSORS])

class DaheimladenSensor(DaheimladenEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, device_class, unit, state_class, icon):
        super().__init__(coordinator, entry, f"sensor_{key}")
        self.key = key
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_icon = icon
        if key in {"raw_station", "raw_transaction", "raw_status", "api_status", "token_expires_at", "idtag_status", "idtag_source", "idtag_discovery"}:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
        if key.startswith("raw_") or key == "idtag_discovery":
            self._attr_entity_registry_enabled_default = False
        if key in {"power_kw", "energy_kwh", "meter_value_kwh", "current", "current_l1", "current_l2", "current_l3", "voltage", "voltage_l1", "voltage_l2", "voltage_l3", "temperature"}:
            self._attr_suggested_display_precision = 2

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        value = data.get(self.key)
        if self._attr_device_class == SensorDeviceClass.TIMESTAMP:
            if not value:
                return None
            if isinstance(value, datetime):
                return value
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except Exception:
                return None
        if isinstance(value, (dict, list)):
            return "available" if value else "empty"
        return value

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        if self.key == "raw_station":
            return data.get("raw_station") or {}
        if self.key == "raw_transaction":
            return data.get("raw_transaction") or {}
        if self.key == "raw_status":
            return data.get("raw_status") or {}
        if self.key == "idtag_discovery":
            return data.get("idtag_discovery") or {}
        return None
