from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN, CONF_PASSWORD

SENSITIVE_KEYS = {
    "password",
    "idtoken",
    "id_token",
    "refreshtoken",
    "refresh_token",
    "authorization",
    "auth_header",
    "api_key",
    "idtag",
    "id_tag",
    "discovered_idtag",
}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_KEYS:
                redacted[key] = "***REDACTED***"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    runtime = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = runtime.get("coordinator")
    api = runtime.get("api")

    config = dict(entry.data)
    config.pop(CONF_PASSWORD, None)
    # Keep support diagnostics shareable. IDTags can authorize remote starts and are redacted.

    data = coordinator.data if coordinator else None

    return {
        "entry": _redact(config),
        "last_update_success": getattr(coordinator, "last_update_success", None),
        "update_interval_seconds": getattr(getattr(coordinator, "update_interval", None), "total_seconds", lambda: None)(),
        "token_expires_at": getattr(api, "expires_at", None),
        "last_charge_rate": getattr(api, "last_charge_rate", None),
        "data": _redact(data),
    }
