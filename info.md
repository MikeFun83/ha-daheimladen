# DaheimLaden / WEEYU v2.3.0

Native Home Assistant custom integration for DaheimLaden / WEEYU wallboxes through the DaheimLaden cloud API.

## Highlights

- Firebase login with automatic token refresh
- Start/stop charging
- Charge current 6–16 A
- Automatic IDTag discovery via `cs:get_cards`
- Energy Dashboard compatible total meter sensor
- Diagnostics with sensitive values redacted
- HACS-ready repository structure

## Security note

The DaheimLaden/Firebase API key is intentionally not hard-coded in this public repository. Existing Home Assistant installations keep the API key in their config entry. For new installations, enter the Firebase API key in the setup dialog.

See the README for instructions on how to find the Firebase API key in the DaheimLaden login request. Never publish `access_token`, `refresh_token`, `id_token`, password, IDTag or real API keys.
