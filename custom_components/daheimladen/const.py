DOMAIN = "daheimladen"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_API_KEY = "api_key"
CONF_STATION_ID = "station_id"
CONF_IDTAG = "idtag"
CONF_AUTH_HEADER = "auth_header"  # legacy v1.0/v1.1 fallback
CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FAST_SCAN_INTERVAL = "fast_scan_interval"
CONF_OFFLINE_SCAN_INTERVAL = "offline_scan_interval"
CONF_DEBUG = "debug"
CONF_LAST_CHARGE_RATE = "last_charge_rate"
CONF_DISCOVERED_IDTAG = "discovered_idtag"
CONF_IDTAG_SOURCE = "idtag_source"
CONF_LAST_IDTAG_DISCOVERY = "last_idtag_discovery"

DEFAULT_API_KEY = ""  # Do not commit vendor/Firebase API keys to public repositories.
DEFAULT_BASE_URL = "https://api.daheimladen.com"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_FAST_SCAN_INTERVAL = 5
DEFAULT_OFFLINE_SCAN_INTERVAL = 60
DEFAULT_CONNECTOR_ID = 1
DEFAULT_CHARGE_RATE = 16

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = f"{DOMAIN}.entry"

SERVICE_START = "start_charge"
SERVICE_STOP = "stop_charge"
SERVICE_SET_CURRENT = "set_current"
SERVICE_REFRESH = "refresh"
SERVICE_DISCOVER_IDTAG = "discover_idtag"
ATTR_STATION_ID = "station_id"
ATTR_AMPERE = "ampere"

PLATFORMS = ["sensor", "binary_sensor", "switch", "number", "button"]
