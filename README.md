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

## Version 2.2.0

- IDTag auto-discovery confirmed via `cs:get_cards`
- IDTag field is optional during setup
- Remote start automatically searches for an IDTag if none is configured
- Manual IDTag remains available as fallback
- IDTags and tokens are redacted in diagnostics
- Based on the stable v2.1.2 codebase
- HACS/GitHub-ready structure


## Security note

The DaheimLaden/Firebase API key is intentionally not hard-coded in this public repository. Existing Home Assistant installations keep the API key in their config entry. For new installations, enter the Firebase API key in the setup dialog.
