from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_EMAIL,
    CONF_IDTAG,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_FAST_SCAN_INTERVAL,
    CONF_OFFLINE_SCAN_INTERVAL,
    CONF_DEBUG,
    CONF_STATION_ID,
    DEFAULT_API_KEY,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_FAST_SCAN_INTERVAL,
    DEFAULT_OFFLINE_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class DaheimladenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 4

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            station_id = str(user_input[CONF_STATION_ID]).strip()
            email = str(user_input[CONF_EMAIL]).strip()
            password = str(user_input[CONF_PASSWORD])
            api_key = str(user_input.get(CONF_API_KEY, DEFAULT_API_KEY)).strip()
            if not api_key:
                errors[CONF_API_KEY] = "required"
                return self.async_show_form(step_id="user", data_schema=_user_schema(user_input), errors=errors)

            try:
                await _test_firebase_login(self.hass, email, password, api_key)
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("DaheimLaden login test failed: %s", err)
                errors["base"] = "auth"
            else:
                await self.async_set_unique_id(station_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"DaheimLaden {station_id}",
                    data={
                        CONF_EMAIL: email,
                        CONF_PASSWORD: password,
                        CONF_API_KEY: api_key,
                        CONF_STATION_ID: station_id,
                        CONF_IDTAG: str(user_input.get(CONF_IDTAG, "") or "").strip(),
                        CONF_BASE_URL: str(user_input.get(CONF_BASE_URL, DEFAULT_BASE_URL)).rstrip("/"),
                    },
                    options={CONF_SCAN_INTERVAL: int(user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))},
                )

        return self.async_show_form(step_id="user", data_schema=_user_schema(user_input), errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return DaheimladenOptionsFlow(config_entry)


class DaheimladenOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        # Do not assign to self.config_entry. In newer Home Assistant versions this
        # attribute is managed by the config flow manager and assigning to it can
        # raise an exception, which makes the options dialog fail with HTTP 500.
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self._config_entry.options.get(
                        CONF_SCAN_INTERVAL,
                        self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                vol.Optional(
                    CONF_FAST_SCAN_INTERVAL,
                    default=self._config_entry.options.get(CONF_FAST_SCAN_INTERVAL, DEFAULT_FAST_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                vol.Optional(
                    CONF_OFFLINE_SCAN_INTERVAL,
                    default=self._config_entry.options.get(CONF_OFFLINE_SCAN_INTERVAL, DEFAULT_OFFLINE_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=30, max=600)),
                vol.Optional(
                    CONF_DEBUG,
                    default=self._config_entry.options.get(CONF_DEBUG, False),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)


def _user_schema(user_input: dict | None = None) -> vol.Schema:
    """Build the user setup schema.

    The Firebase API key is intentionally not hard-coded in the public repository,
    because GitHub secret scanning flags Google API keys. Existing config entries
    keep their stored value; new installs must provide the DaheimLaden Firebase key.
    """
    defaults = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_EMAIL, default=defaults.get(CONF_EMAIL, "")): str,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): str,
            vol.Required(CONF_STATION_ID, default=defaults.get(CONF_STATION_ID, "")): str,
            vol.Optional(CONF_IDTAG, default=defaults.get(CONF_IDTAG, "")): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)): int,
            vol.Optional(CONF_BASE_URL, default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL)): str,
            vol.Required(CONF_API_KEY, default=defaults.get(CONF_API_KEY, DEFAULT_API_KEY)): str,
        }
    )

async def _test_firebase_login(hass, email: str, password: str, api_key: str) -> None:
    session = async_get_clientsession(hass)
    # Browser currently uses v3/relyingparty/verifyPassword. The v1 endpoint also works for most
    # Firebase projects, but using v3 here mirrors DaheimLaden's portal exactly.
    url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={api_key}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    async with session.post(url, json=payload, timeout=20) as resp:
        if resp.status >= 400:
            text = await resp.text()
            raise RuntimeError(f"Firebase login failed: {resp.status} {text}")
        data = await resp.json(content_type=None)
        if not data.get("idToken") or not data.get("refreshToken"):
            raise RuntimeError("Firebase login response did not contain idToken/refreshToken")
