from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from .api import DaheimladenApi
from .coordinator import DaheimladenCoordinator
from .const import (
    ATTR_AMPERE,
    ATTR_STATION_ID,
    CONF_SCAN_INTERVAL,
    CONF_FAST_SCAN_INTERVAL,
    CONF_OFFLINE_SCAN_INTERVAL,
    CONF_DEBUG,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_OFFLINE_SCAN_INTERVAL,
    DOMAIN,
    STORAGE_KEY_PREFIX,
    STORAGE_VERSION,
    PLATFORMS,
    SERVICE_REFRESH,
    SERVICE_DISCOVER_IDTAG,
    SERVICE_SET_CURRENT,
    SERVICE_START,
    SERVICE_STOP,
)

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_STATION = vol.Schema({vol.Optional(ATTR_STATION_ID): cv.string})
SERVICE_SCHEMA_SET_CURRENT = vol.Schema({
    vol.Optional(ATTR_STATION_ID): cv.string,
    vol.Required(ATTR_AMPERE): vol.All(vol.Coerce(int), vol.Range(min=6, max=16)),
})


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up global DaheimLaden services."""

    async def _get_runtime(call: ServiceCall):
        station_id = call.data.get(ATTR_STATION_ID)
        runtimes = hass.data.get(DOMAIN, {})
        if not runtimes:
            raise ValueError("No DaheimLaden integration entry configured")
        if station_id:
            for runtime in runtimes.values():
                if runtime["api"].station_id == str(station_id):
                    return runtime
            raise ValueError(f"No DaheimLaden station found for station_id {station_id}")
        if len(runtimes) > 1:
            raise ValueError("Multiple DaheimLaden stations configured; pass station_id")
        return next(iter(runtimes.values()))

    async def _start(call: ServiceCall) -> None:
        runtime = await _get_runtime(call)
        await runtime["api"].remote_start()
        await runtime["coordinator"].async_request_refresh()

    async def _stop(call: ServiceCall) -> None:
        runtime = await _get_runtime(call)
        await runtime["api"].remote_stop()
        await runtime["coordinator"].async_request_refresh()

    async def _set_current(call: ServiceCall) -> None:
        runtime = await _get_runtime(call)
        await runtime["api"].set_charge_rate(call.data[ATTR_AMPERE])
        await runtime["coordinator"].async_request_refresh()

    async def _refresh(call: ServiceCall) -> None:
        runtime = await _get_runtime(call)
        await runtime["coordinator"].async_request_refresh()

    async def _discover_idtag(call: ServiceCall) -> None:
        runtime = await _get_runtime(call)
        await runtime["api"].discover_idtag(force=True)
        await runtime["coordinator"].async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_START, _start, schema=SERVICE_SCHEMA_STATION)
    hass.services.async_register(DOMAIN, SERVICE_STOP, _stop, schema=SERVICE_SCHEMA_STATION)
    hass.services.async_register(DOMAIN, SERVICE_SET_CURRENT, _set_current, schema=SERVICE_SCHEMA_SET_CURRENT)
    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _refresh, schema=SERVICE_SCHEMA_STATION)
    hass.services.async_register(DOMAIN, SERVICE_DISCOVER_IDTAG, _discover_idtag, schema=SERVICE_SCHEMA_STATION)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}_{entry.entry_id}")
    stored_data = await store.async_load() or {}

    api = DaheimladenApi(hass, entry.data, store=store, stored_data=stored_data)
    scan_interval = int(entry.options.get(CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)))

    if entry.options.get(CONF_DEBUG):
        _LOGGER.setLevel(logging.DEBUG)

    coordinator = DaheimladenCoordinator(
        hass,
        api,
        name=f"DaheimLaden {entry.data.get('station_id')}",
        standby_interval=scan_interval,
        fast_interval=int(entry.options.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL)),
        offline_interval=int(entry.options.get(CONF_OFFLINE_SCAN_INTERVAL, DEFAULT_OFFLINE_SCAN_INTERVAL)),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
        "store": store,
    }

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the integration when options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older config entries."""
    if entry.version < 4:
        hass.config_entries.async_update_entry(entry, version=4)
    return True
