from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from aiohttp import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_AUTH_HEADER,
    CONF_BASE_URL,
    CONF_DISCOVERED_IDTAG,
    CONF_EMAIL,
    CONF_IDTAG,
    CONF_IDTAG_SOURCE,
    CONF_LAST_CHARGE_RATE,
    CONF_LAST_IDTAG_DISCOVERY,
    CONF_PASSWORD,
    CONF_STATION_ID,
    DEFAULT_API_KEY,
    DEFAULT_BASE_URL,
    DEFAULT_CHARGE_RATE,
    DEFAULT_CONNECTOR_ID,
)

_LOGGER = logging.getLogger(__name__)

_IDTAG_EXCLUDED_KEY_PARTS = (
    "token",
    "refresh",
    "password",
    "secret",
    "authorization_header",
    "transaction_id",
    "station_id",
    "charging_station_id",
)

_IDTAG_KEY_WEIGHTS = (
    ("idtag", 100),
    ("id_tag", 100),
    ("id-tag", 100),
    ("id tag", 100),
    ("rfid_tag", 90),
    ("rfid", 85),
    ("auth_tag", 85),
    ("authorization_tag", 85),
    ("authorizationtag", 85),
    ("tag_id", 75),
    ("tagid", 75),
    ("card_id", 70),
    ("cardid", 70),
    ("badge", 70),
    ("tag", 60),
)

_STATION_PROBE_ENDPOINTS = (
    "get_chargingstation",
    "status",
    "get_latest_inprogress_transaction",
    "get_settings",
    "get_cards",
    "get_card",
    "get_idtag",
    "get_idtags",
    "get_id_tag",
    "get_id_tags",
    "get_rfid",
    "get_rfids",
    "get_tag",
    "get_tags",
    "get_badge",
    "get_badges",
    "get_authorization",
    "get_authorizations",
    "get_authorization_tags",
    "get_access",
    "get_accesses",
    "get_user",
    "get_users",
    "get_connectors",
)

_ROOT_PROBE_PATHS = (
    "/v1/me",
    "/v1/user",
    "/v1/user/me",
    "/v1/users/me",
    "/v1/account",
    "/v1/accounts/me",
    "/v1/idtag",
    "/v1/idtags",
    "/v1/id_tag",
    "/v1/id_tags",
    "/v1/rfid",
    "/v1/rfids",
    "/v1/tag",
    "/v1/tags",
    "/v1/card",
    "/v1/cards",
    "/v1/badge",
    "/v1/badges",
    "/v1/authorization",
    "/v1/authorizations",
    "/v1/authorization_tags",
    "/v1/chargingstations",
    "/v1/charging_stations",
    "/v1/cs",
)


class DaheimladenApi:
    def __init__(self, hass: HomeAssistant, config: dict[str, Any], store: Any | None = None, stored_data: dict[str, Any] | None = None) -> None:
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.station_id = str(config[CONF_STATION_ID])

        stored_data = stored_data or {}
        manual_idtag = str(config.get(CONF_IDTAG, "") or "").strip()
        stored_idtag = str(stored_data.get(CONF_DISCOVERED_IDTAG, "") or "").strip()
        self.manual_idtag = manual_idtag
        self.discovered_idtag = stored_idtag
        self.idtag = manual_idtag or stored_idtag
        self.idtag_source = str(
            stored_data.get(CONF_IDTAG_SOURCE)
            or ("manual_config" if manual_idtag else ("stored_discovery" if stored_idtag else "unknown"))
        )
        self.idtag_discovery: dict[str, Any] = {
            "status": "manual_configured" if manual_idtag else ("stored_discovery" if stored_idtag else "not_checked"),
            "source": self.idtag_source,
            "has_idtag": bool(self.idtag),
        }
        self._idtag_discovery_attempted = bool(self.idtag)

        self.base_url = str(config.get(CONF_BASE_URL, DEFAULT_BASE_URL)).rstrip("/")
        self.connector_id = DEFAULT_CONNECTOR_ID
        self.last_data: dict[str, Any] = {}
        self.store = store

        self.last_charge_rate = _normalize_charge_rate(
            stored_data.get(CONF_LAST_CHARGE_RATE) or config.get(CONF_LAST_CHARGE_RATE),
            DEFAULT_CHARGE_RATE,
        )

        self.email = str(config.get(CONF_EMAIL, ""))
        self.password = str(config.get(CONF_PASSWORD, ""))
        self.api_key = str(config.get(CONF_API_KEY, DEFAULT_API_KEY) or "").strip()
        self.legacy_auth_header = str(config.get(CONF_AUTH_HEADER, ""))

        self.id_token: str | None = None
        self.refresh_token: str | None = None
        self.expires_at: float = 0

    @property
    def uses_firebase(self) -> bool:
        return bool(self.email and self.password)

    @property
    def headers(self) -> dict[str, str]:
        token = self.id_token
        auth = f"Bearer {token}" if token else self.legacy_auth_header
        return {
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }

    def _url(self, endpoint: str) -> str:
        return f"{self.base_url}/v1/cs/{self.station_id}/{endpoint}"

    async def _ensure_token(self) -> None:
        if not self.uses_firebase:
            return
        if self.id_token and time.time() < self.expires_at - 120:
            return
        if self.refresh_token:
            try:
                await self._refresh_id_token()
                return
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("DaheimLaden token refresh failed, doing full login: %s", err)
        await self._login()

    async def _login(self) -> None:
        if not self.api_key:
            raise RuntimeError("DaheimLaden Firebase API key is missing. Reconfigure the integration and enter the API key.")
        # DaheimLaden currently uses Firebase Identity Toolkit. The v3 endpoint mirrors the portal.
        url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={self.api_key}"
        payload = {"email": self.email, "password": self.password, "returnSecureToken": True}
        async with self.session.post(url, json=payload, timeout=20) as resp:
            text = await resp.text()
            if resp.status >= 400:
                _LOGGER.error("DaheimLaden Firebase login failed: %s", text)
                resp.raise_for_status()
            data = await resp.json(content_type=None)
        self._store_token_response(data)

    async def _refresh_id_token(self) -> None:
        if not self.refresh_token:
            raise RuntimeError("No refresh token available")
        if not self.api_key:
            raise RuntimeError("DaheimLaden Firebase API key is missing. Reconfigure the integration and enter the API key.")
        url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        payload = {"grant_type": "refresh_token", "refresh_token": self.refresh_token}
        async with self.session.post(url, json=payload, timeout=20) as resp:
            text = await resp.text()
            if resp.status >= 400:
                _LOGGER.debug("DaheimLaden Firebase refresh failed: %s", text)
                resp.raise_for_status()
            data = await resp.json(content_type=None)
        self.id_token = data.get("id_token") or data.get("idToken")
        self.refresh_token = data.get("refresh_token") or data.get("refreshToken") or self.refresh_token
        expires_in = _as_int(data.get("expires_in") or data.get("expiresIn")) or 3600
        self.expires_at = time.time() + expires_in
        if not self.id_token:
            raise RuntimeError("Refresh response did not contain id_token")

    def _store_token_response(self, data: dict[str, Any]) -> None:
        self.id_token = data.get("idToken") or data.get("id_token")
        self.refresh_token = data.get("refreshToken") or data.get("refresh_token") or self.refresh_token
        expires_in = _as_int(data.get("expiresIn") or data.get("expires_in")) or 3600
        self.expires_at = time.time() + expires_in
        if not self.id_token or not self.refresh_token:
            raise RuntimeError("Login response did not contain idToken/refreshToken")

    async def _request(self, method: str, endpoint: str, json: dict[str, Any] | None = None, *, retry: bool = True) -> Any:
        await self._ensure_token()
        url = self._url(endpoint)
        try:
            async with self.session.request(method, url, headers=self.headers, json=json, timeout=20) as resp:
                text = await resp.text()
                if resp.status == 401 and retry and self.uses_firebase:
                    _LOGGER.debug("DaheimLaden API returned 401, refreshing token and retrying %s", endpoint)
                    self.id_token = None
                    await self._refresh_id_token() if self.refresh_token else await self._login()
                    return await self._request(method, endpoint, json, retry=False)
                if resp.status >= 400:
                    _LOGGER.error("DaheimLaden API error %s %s: %s", resp.status, endpoint, text)
                    resp.raise_for_status()
                try:
                    return await resp.json(content_type=None)
                except Exception:
                    return {"raw_response": text, "status_code": resp.status}
        except ClientResponseError:
            raise

    async def _probe_absolute(self, method: str, url: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """Probe a possible discovery endpoint without logging expected 404/405 errors."""
        await self._ensure_token()
        try:
            async with self.session.request(method, url, headers=self.headers, json=json, timeout=15) as resp:
                text = await resp.text()
                parsed: Any
                try:
                    parsed = await resp.json(content_type=None)
                except Exception:
                    parsed = {"raw_response": text[:500]} if text else {}
                return {
                    "ok": 200 <= resp.status < 300,
                    "status_code": resp.status,
                    "data": parsed,
                }
        except Exception as err:  # noqa: BLE001
            return {"ok": False, "error": str(err)}

    async def _firebase_account_info(self) -> dict[str, Any]:
        await self._ensure_token()
        if not self.id_token:
            return {}
        url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={self.api_key}"
        payload = {"idToken": self.id_token}
        result = await self._probe_absolute("POST", url, json=payload)
        data = result.get("data") if result.get("ok") else {}
        return data if isinstance(data, dict) else {"value": data}

    async def get_chargingstation(self) -> dict[str, Any]:
        data = await self._request("GET", "get_chargingstation")
        return data if isinstance(data, dict) else {"value": data}

    async def get_latest_inprogress_transaction(self) -> dict[str, Any]:
        data = await self._request("GET", "get_latest_inprogress_transaction")
        return data if isinstance(data, dict) else {"value": data}

    async def get_status(self) -> dict[str, Any]:
        try:
            data = await self._request("GET", "status")
            return data if isinstance(data, dict) else {"value": data}
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("status failed: %s", err)
            return {}

    async def get_settings(self) -> dict[str, Any]:
        try:
            data = await self._request("GET", "get_settings")
            return data if isinstance(data, dict) else {"value": data}
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("get_settings failed: %s", err)
            return {}

    async def discover_idtag(self, *, force: bool = False) -> dict[str, Any]:
        """Best-effort IDTag discovery.

        Only GET probes and Firebase account lookup are used. The method is intentionally
        conservative: a found value is only used automatically when no manual IDTag is set.
        """
        if self.manual_idtag and not force:
            self.idtag_discovery = {
                "status": "manual_configured",
                "source": "manual_config",
                "has_idtag": True,
            }
            return self.idtag_discovery

        if self._idtag_discovery_attempted and not force:
            return self.idtag_discovery

        self._idtag_discovery_attempted = True
        checked: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []

        async def _scan(source: str, payload: Any, status_code: int | None = None) -> None:
            checked.append({"source": source, "status_code": status_code})
            for candidate in _extract_idtag_candidates(payload, source):
                candidates.append(candidate)

        try:
            account_info = await self._firebase_account_info()
            await _scan("firebase:getAccountInfo", account_info, 200 if account_info else None)
        except Exception as err:  # noqa: BLE001
            checked.append({"source": "firebase:getAccountInfo", "error": str(err)})

        # Existing known endpoints can also contain nested authorization/tag data on some accounts.
        for endpoint in ("get_chargingstation", "get_latest_inprogress_transaction", "status", "get_settings"):
            try:
                data = await self._request("GET", endpoint)
                await _scan(f"cs:{endpoint}", data, 200)
            except Exception as err:  # noqa: BLE001
                checked.append({"source": f"cs:{endpoint}", "error": str(err)})

        for endpoint in _STATION_PROBE_ENDPOINTS:
            if endpoint in {"get_chargingstation", "get_latest_inprogress_transaction", "status", "get_settings"}:
                continue
            url = self._url(endpoint)
            result = await self._probe_absolute("GET", url)
            checked.append({"source": f"cs:{endpoint}", "status_code": result.get("status_code"), "ok": result.get("ok", False)})
            if result.get("ok"):
                for candidate in _extract_idtag_candidates(result.get("data"), f"cs:{endpoint}"):
                    candidates.append(candidate)
            # DaheimLaden/WEEYU has been confirmed to expose the IDTag via cs:get_cards.
            # Stop probing once we have a high-confidence station candidate to avoid many
            # unnecessary 404/405 requests during setup or remote start.
            if _select_idtag_candidate(_dedupe_candidates(candidates)) is not None:
                break

        candidates = _dedupe_candidates(candidates)
        selected = _select_idtag_candidate(candidates)

        if selected is None:
            for path in _ROOT_PROBE_PATHS:
                url = f"{self.base_url}{path}"
                result = await self._probe_absolute("GET", url)
                checked.append({"source": f"root:{path}", "status_code": result.get("status_code"), "ok": result.get("ok", False)})
                if result.get("ok"):
                    for candidate in _extract_idtag_candidates(result.get("data"), f"root:{path}"):
                        candidates.append(candidate)
                if _select_idtag_candidate(_dedupe_candidates(candidates)) is not None:
                    break

            candidates = _dedupe_candidates(candidates)
            selected = _select_idtag_candidate(candidates)

        status = "not_found"
        if selected:
            found_value = str(selected["value"])
            if self.manual_idtag:
                status = "found_matches_manual" if found_value == self.manual_idtag else "found_differs_from_manual"
                # Keep the manually configured IDTag as the active value.
                self.discovered_idtag = found_value
            else:
                status = "discovered"
                self.discovered_idtag = found_value
                self.idtag = found_value
                self.idtag_source = str(selected.get("source") or "discovery")
        elif self.manual_idtag:
            status = "manual_configured_not_found_by_scan"

        self.idtag_discovery = {
            "status": status,
            "has_idtag": bool(self.idtag),
            "source": self.idtag_source if self.idtag else None,
            "selected": _redact_candidate(selected) if selected else None,
            "candidate_count": len(candidates),
            "candidates": [_redact_candidate(candidate) for candidate in candidates[:20]],
            "checked_count": len(checked),
            "checked": checked,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        if selected:
            await self._remember_idtag(
                str(selected["value"]),
                str(selected.get("source") or "discovery"),
                discovery_only=bool(self.manual_idtag),
            )
        elif not selected and self.store is not None:
            await self._save_store_extra({
                CONF_LAST_IDTAG_DISCOVERY: self.idtag_discovery,
            })
        return self.idtag_discovery

    async def _remember_idtag(self, idtag: str, source: str, *, discovery_only: bool = False) -> None:
        self.discovered_idtag = idtag
        if not discovery_only and not self.manual_idtag:
            self.idtag = idtag
            self.idtag_source = source
        await self._save_store_extra({
            CONF_DISCOVERED_IDTAG: idtag,
            CONF_IDTAG_SOURCE: source,
            CONF_LAST_IDTAG_DISCOVERY: self.idtag_discovery,
            "idtag_updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        })

    async def _save_store_extra(self, extra: dict[str, Any]) -> None:
        if self.store is None:
            return
        current = await self.store.async_load() or {}
        current.update(extra)
        await self.store.async_save(current)

    async def async_update(self) -> dict[str, Any]:
        station = await self.get_chargingstation()
        tx = await self.get_latest_inprogress_transaction()
        status_live = await self.get_status()
        settings = await self.get_settings()

        if not self.idtag and not self._idtag_discovery_attempted and self.uses_firebase:
            try:
                await self.discover_idtag(force=False)
            except Exception as err:  # noqa: BLE001
                self.idtag_discovery = {
                    "status": "error",
                    "error": str(err),
                    "has_idtag": False,
                    "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                }

        transaction_id = _as_int(tx.get("transaction_id", 0)) or 0
        api_status = str(status_live.get("status") or "").strip()
        tx_status = deep_find(tx, ["status", "charging_status", "transaction_status"])

        raw_status = api_status or (str(tx_status) if tx_status not in (None, "", 0) else "")
        raw_status_lower = raw_status.lower()
        is_charging = bool(transaction_id > 0) or raw_status_lower in ("charging", "inprogress", "in_progress")
        is_connected = is_charging or raw_status_lower in ("preparing", "suspendedev", "suspended_ev", "suspendedevse", "suspended_evse")
        if not raw_status:
            raw_status = "Charging" if is_charging else "Available"

        status_label = _status_label(raw_status, is_charging)

        charge_rate = deep_find(settings, ["ChargeRate", "charge_rate", "chargerate", "current", "ampere", "amps"])

        v1 = _as_float(status_live.get("voltage_phase_l1l2"))
        v2 = _as_float(status_live.get("voltage_phase_l2l3"))
        v3 = _as_float(status_live.get("voltage_phase_l3l1"))
        a1 = _as_float(status_live.get("current_import_phase_l1"))
        a2 = _as_float(status_live.get("current_import_phase_l2"))
        a3 = _as_float(status_live.get("current_import_phase_l3"))

        currents = [x for x in (a1, a2, a3) if x is not None]
        voltages = [x for x in (v1, v2, v3) if x is not None]
        current_avg = round(sum(currents) / len(currents), 2) if currents else None
        voltage_avg = round(sum(voltages) / len(voltages), 2) if voltages else None

        # DaheimLaden currently allows setting ChargeRate, but does not always return it.
        # Prefer a value returned by the API. Otherwise keep the last known/set value so
        # Home Assistant does not show the number entity as unknown after a restart.
        charge_rate_value = _normalize_charge_rate(charge_rate)
        if charge_rate_value is not None:
            self.last_charge_rate = charge_rate_value
        elif self.last_charge_rate is not None:
            charge_rate_value = self.last_charge_rate
        elif is_charging and current_avg is not None and current_avg > 0:
            # Last resort: show a best-effort estimate while charging.
            charge_rate_value = _normalize_charge_rate(current_avg, DEFAULT_CHARGE_RATE)
        else:
            charge_rate_value = DEFAULT_CHARGE_RATE

        power_kw = _as_float(status_live.get("active_power_import"))
        if power_kw is None:
            power_kw = _as_float(deep_find(tx, [
                "power_kw", "charging_power_kw", "current_power_kw", "actual_power_kw", "power", "charging_power", "current_power"
            ]))
            if power_kw is not None and power_kw > 100:
                power_kw = round(power_kw / 1000, 3)
        if power_kw is None and currents and voltages:
            # The API exposes phase-to-phase voltages. Approximate line-to-neutral voltage by /sqrt(3).
            power_kw = round(sum((voltages[i] / 1.732) * currents[i] for i in range(min(len(voltages), len(currents)))) / 1000, 3)

        current_time = status_live.get("current_time")
        transaction_start_at = status_live.get("transaction_start_at")
        duration_seconds = _as_int(deep_find(tx, ["duration_seconds", "charging_time_seconds", "elapsed_seconds", "duration", "charging_time"]))
        if duration_seconds is None:
            duration_seconds = _duration_from_iso(transaction_start_at, current_time)
        if duration_seconds is None and not is_charging:
            duration_seconds = 0

        data = {
            "station": station,
            "transaction": tx,
            "settings": settings,
            "live_status": status_live,
            "transaction_id": transaction_id,
            "status": status_label,
            "api_status": raw_status,
            "is_charging": is_charging,
            "is_connected": is_connected,
            "is_online": True,
            "idtag_configured": bool(self.idtag),
            "idtag_status": self.idtag_discovery.get("status") or ("manual_configured" if self.idtag else "not_checked"),
            "idtag_source": self.idtag_source if self.idtag else None,
            "idtag_discovery": self.idtag_discovery,
            "charge_rate": charge_rate_value,
            "manufacturer": station.get("charging_station_vendor"),
            "model": station.get("charging_station_model"),
            "max_power_kw": _as_float(station.get("max_charging_power_in_kw")),
            "phases": _as_int(station.get("phases")),
            "voltage_l1": v1,
            "voltage_l2": v2,
            "voltage_l3": v3,
            "current_l1": a1,
            "current_l2": a2,
            "current_l3": a3,
            "temperature": _as_float(status_live.get("charging_station_temperature")),
            "current_time": current_time,
            "transaction_start_at": transaction_start_at if transaction_start_at not in ("0", 0, "") else None,
            "current": current_avg,
            "voltage": voltage_avg,
            "power_kw": power_kw,
            "meter_value_kwh": _wh_to_kwh(status_live.get("total_meter_value")),
            "energy_kwh": _wh_to_kwh(status_live.get("transaction_power_used")),
            "duration_seconds": duration_seconds,
            "last_update": datetime.now().astimezone().isoformat(timespec="seconds"),
            "token_expires_at": datetime.fromtimestamp(self.expires_at).astimezone().isoformat(timespec="seconds") if self.expires_at else None,
            "station_id": self.station_id,
            "raw_station": station,
            "raw_transaction": tx,
            "raw_status": status_live,
        }

        if data["energy_kwh"] is None:
            energy = _as_float(deep_find(tx, [
                "energy_kwh", "charged_energy_kwh", "meter_kwh", "consumed_energy_kwh", "energy", "charged_energy", "meter_value"
            ]))
            if energy is not None and energy > 1000:
                energy = round(energy / 1000, 3)
            data["energy_kwh"] = energy

        self.last_data = data
        return data

    async def remote_start(self) -> Any:
        if not self.idtag:
            await self.discover_idtag(force=False)
        if not self.idtag:
            raise ValueError("No idtag configured or discovered for remotestart")
        return await self._request("POST", "remotestart", {
            "connector_id": self.connector_id,
            "idtag": self.idtag,
        })

    async def remote_stop(self, transaction_id: int | None = None) -> Any:
        if transaction_id is None:
            transaction_id = int(self.last_data.get("transaction_id") or 0)
        if not transaction_id:
            latest = await self.get_latest_inprogress_transaction()
            transaction_id = int(latest.get("transaction_id") or 0)
        if not transaction_id:
            raise ValueError("No active transaction_id available for remotestop")
        return await self._request("POST", "remotestop", {"transaction_id": transaction_id})

    async def set_charge_rate(self, ampere: int) -> Any:
        ampere = _normalize_charge_rate(ampere, DEFAULT_CHARGE_RATE) or DEFAULT_CHARGE_RATE
        response = await self._request("POST", "change_config", {
            "charging_station_id": self.station_id,
            "key": "ChargeRate",
            "value": str(ampere),
        })
        await self._remember_charge_rate(ampere)
        return response

    async def _remember_charge_rate(self, ampere: int) -> None:
        self.last_charge_rate = _normalize_charge_rate(ampere, DEFAULT_CHARGE_RATE) or DEFAULT_CHARGE_RATE
        if self.last_data is not None:
            self.last_data["charge_rate"] = self.last_charge_rate
        await self._save_store_extra({
            CONF_LAST_CHARGE_RATE: self.last_charge_rate,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        })


def _status_label(raw_status: str, is_charging: bool) -> str:
    status = (raw_status or "").strip().lower()
    if is_charging or status == "charging":
        return "Lädt"
    if status == "preparing":
        return "Verbunden"
    if status in ("available", "ready"):
        return "Bereit"
    if status in ("finishing", "finished", "completed"):
        return "Beendet"
    if status in ("faulted", "error"):
        return "Fehler"
    if status in ("offline", "unavailable"):
        return "Offline"
    return raw_status or "Unbekannt"


def _as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def _as_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except Exception:
        return None


def _normalize_charge_rate(value: Any, default: int | None = None) -> int | None:
    ampere = _as_int(value)
    if ampere is None:
        return default
    return max(6, min(16, ampere))


def _to_kwh(value: Any) -> float | None:
    """Best-effort conversion for unknown energy fields.

    Some historic API fields are already kWh, larger raw meter values are Wh.
    """
    numeric = _as_float(value)
    if numeric is None:
        return None
    if numeric > 1000:
        return round(numeric / 1000, 3)
    return numeric


def _wh_to_kwh(value: Any) -> float | None:
    """Convert DaheimLaden Wh fields to kWh.

    The /status endpoint exposes total_meter_value and transaction_power_used in Wh.
    Even small values like 300 mean 300 Wh = 0.3 kWh.
    """
    numeric = _as_float(value)
    if numeric is None:
        return None
    return round(numeric / 1000, 3)


def _duration_from_iso(start: Any, end: Any) -> int | None:
    if not start or not end or start in ("0", 0) or end in ("0", 0):
        return None
    try:
        start_dt = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        seconds = int((end_dt - start_dt).total_seconds())
        return seconds if seconds >= 0 else None
    except Exception:
        return None


def deep_find(data: Any, keys: list[str]) -> Any:
    wanted = {k.lower(): k for k in keys}

    def _walk(obj: Any) -> Any:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if str(k).lower() in wanted:
                    return v
            for v in obj.values():
                found = _walk(v)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = _walk(item)
                if found is not None:
                    return found
        return None

    return _walk(data)


def _extract_idtag_candidates(data: Any, source: str) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def _walk(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                key_str = str(key)
                current_path = f"{path}.{key_str}" if path else key_str
                score = _score_idtag_key(current_path)
                if score and _looks_like_idtag_value(value):
                    candidates.append({
                        "value": str(value).strip(),
                        "source": source,
                        "path": current_path,
                        "score": score,
                    })
                _walk(value, current_path)
        elif isinstance(obj, list):
            for idx, item in enumerate(obj):
                _walk(item, f"{path}[{idx}]")
        else:
            # Some endpoints may return a plain list of tag strings, e.g. /v1/idtags.
            source_path = f"{source}.{path}" if path else source
            score = _score_idtag_key(source_path)
            if score and _looks_like_idtag_value(obj):
                candidates.append({
                    "value": str(obj).strip(),
                    "source": source,
                    "path": path or "value",
                    "score": score,
                })

    _walk(data)
    return candidates


def _score_idtag_key(path: str) -> int | None:
    lower = path.lower().replace("-", "_")
    if any(part in lower for part in _IDTAG_EXCLUDED_KEY_PARTS):
        return None
    for key_part, score in _IDTAG_KEY_WEIGHTS:
        normalized = key_part.lower().replace("-", "_")
        if normalized in lower:
            return score
    return None


def _looks_like_idtag_value(value: Any) -> bool:
    if not isinstance(value, (str, int)):
        return False
    text = str(value).strip()
    if not 4 <= len(text) <= 64:
        return False
    if "@" in text or "://" in text:
        return False
    if text.lower() in {"true", "false", "none", "null", "unknown", "available"}:
        return False
    if text.count(".") >= 2:  # avoid JWT-like tokens
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-:.")
    return all(char in allowed for char in text)


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_value: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        value = str(candidate.get("value") or "")
        if not value:
            continue
        existing = by_value.get(value)
        if existing is None or int(candidate.get("score") or 0) > int(existing.get("score") or 0):
            by_value[value] = candidate
    return sorted(by_value.values(), key=lambda item: int(item.get("score") or 0), reverse=True)


def _select_idtag_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    best = candidates[0]
    score = int(best.get("score") or 0)
    if score >= 85:
        return best
    # If there is only one weaker candidate, use it as a best-effort fallback.
    if len(candidates) == 1 and score >= 60:
        return best
    return None


def _redact_candidate(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if not candidate:
        return None
    redacted = dict(candidate)
    value = str(redacted.get("value") or "")
    redacted["value"] = _redact_string(value)
    return redacted


def _redact_string(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "***"
    return f"{value[:2]}***{value[-2:]}"
