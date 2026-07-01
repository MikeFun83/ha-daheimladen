# Changelog

## v2.3.0-dev1

- Removed hard-coded Google/Firebase API key from the public repository.
- Firebase API key is now required during setup.
- Existing installations keep their already stored API key.
- Added clearer error if the API key is missing.


## 2.2.0

- Added automatic IDTag discovery via the DaheimLaden card endpoint (`cs:get_cards`).
- Made the IDTag field optional during setup.
- Added diagnostic button `IDTag suchen`.
- Added service `daheimladen.discover_idtag`.
- Added diagnostic sensors for IDTag status and IDTag source.
- Remote start automatically searches for an IDTag if none is configured.
- Manual IDTag remains supported and takes priority.
- Optimized IDTag discovery to stop after a high-confidence match.
- Diagnostics redact IDTags, tokens, passwords and API keys.
- Kept the v2.1.2 options-flow fix and persisted charge-current handling.

## 2.1.2

- Fixed options/configuration dialog failing with HTTP 500 in newer Home Assistant versions.
- Options are applied by reloading the config entry after saving.
- Updated manifest version to 2.1.2.

## 2.1.1

- Persisted last known/set charge current across Home Assistant restarts.
- Avoided `unknown` for the charge-current number entity when DaheimLaden does not return `ChargeRate`.
- Made the configured-charge-current sensor use the same persisted value.
- Kept HACS/GitHub repository structure clean.

## 2.1.0

- Removed `get_config` because the API returned HTTP 405.
- Fixed energy sensor state-class handling.
- Added polling options for standby, charging and offline states.
- Added diagnostics/raw-data support.
- Added HACS structure.