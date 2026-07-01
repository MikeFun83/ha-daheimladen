# DaheimLaden / WEEYU Home Assistant Integration

Custom integration for DaheimLaden / WEEYU wallboxes via the DaheimLaden cloud API.

## Features

- Firebase login with automatic token refresh
- Cloud polling via `https://api.daheimladen.com`
- Automatic IDTag discovery via the DaheimLaden card endpoint
- Optional manual IDTag fallback
- Start/stop charging
- Set charge current from 6 to 16 A
- Live status via `/status`
- Power, current, voltage, temperature and meter sensors
- Session energy and total meter energy
- Binary sensors for charging, online and vehicle connected
- Diagnostics support with sensitive values redacted
- Home Assistant services
- HACS-ready repository structure

## Installation manually

Copy `custom_components/daheimladen` to `/config/custom_components/daheimladen` and restart Home Assistant.

## HACS custom repository

1. Create a GitHub repository with this structure.
2. Add it in HACS as a custom repository.
3. Category: `Integration`.
4. Install the integration from HACS.
5. Restart Home Assistant.

## Configuration

Add the integration through **Settings → Devices & services → Add integration → DaheimLaden / WEEYU**.

Required values:

- DaheimLaden e-mail
- DaheimLaden password
- Station ID
- Firebase API-Key

Optional values:

- IDTag

The IDTag field can stay empty. The integration will try to discover it automatically through the DaheimLaden cloud. A manually configured IDTag is still supported and takes priority.

## Controls

The integration provides:

- Switch: **Laden**
- Button: **Laden starten**
- Button: **Laden stoppen**
- Number: **Ladestrom** from 6 to 16 A
- Diagnostic button: **IDTag suchen**

## Energy Dashboard

Use the sensor **Zählerstand** for Home Assistant Energy.

The sensor has:

- `device_class: energy`
- `state_class: total_increasing`
- `unit_of_measurement: kWh`

Do not use **Geladene Energie aktuelle Ladung** for the Energy Dashboard. That value is only the energy of the current/last session.

## Services

The integration exposes these services:

- `daheimladen.start_charge`
- `daheimladen.stop_charge`
- `daheimladen.set_current`
- `daheimladen.refresh`
- `daheimladen.discover_idtag`

## Firebase API-Key

The integration uses the DaheimLaden cloud API. The login is handled through Firebase Identity Toolkit.

For security reasons, this repository does **not** include a Firebase API key. New installations must enter the Firebase Web API key during setup. Existing Home Assistant installations keep their already stored API key when the integration is updated.

The Firebase API key is **not** one of these values:

- `access_token`
- `refresh_token`
- `id_token`
- `user_id`
- `project_id`

These values are personal login/session data and must never be shared publicly.

### How to find the Firebase API key

1. Open the DaheimLaden web portal in your browser.
2. Open the browser developer tools.
   - Chrome / Edge: press `F12`
   - or right-click → **Inspect**
3. Open the **Network** tab.
4. Log in to DaheimLaden.
5. Look for a request containing one of these names:
   - `verifyPassword`
   - `signInWithPassword`
6. Open that request and switch to **Headers**.
7. Check the **Request URL**. It usually looks similar to one of these examples:

```text
https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=YOUR_FIREBASE_WEB_API_KEY
```

or:

```text
https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key=YOUR_FIREBASE_WEB_API_KEY
```

The Firebase API key is the value after:

```text
key=
```

Enter this value in Home Assistant during setup in the field **Firebase API-Key**.

Do not publish the real key in GitHub, screenshots, issues or logs.

## Version 2.3.0

- Removed hard-coded Google/Firebase API key from the public repository
- Firebase API key is required during new setup
- Existing installations keep their already stored API key
- Added README instructions for finding the Firebase API key without exposing tokens
- Kept automatic IDTag discovery via `cs:get_cards`
- Kept start/stop charging and charge-current control
- HACS/GitHub-ready structure
