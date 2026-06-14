"""Konstanten für die Waveshare PoE Relay Integration."""

DOMAIN = "waveshare_relay"
VERSION = "1.1.0"

# Config keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_POLL_INTERVAL = "poll_interval"
CONF_RELAY_NAMES = "relay_names"
CONF_RELAY_COUNT = "relay_count"

# Defaults
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
DEFAULT_POLL_INTERVAL = 2
DEFAULT_RELAY_COUNT = 8
SUPPORTED_RELAY_COUNTS = (8, 16, 30)
RELAY_COUNT_MODELS = {
    8: "Modbus POE ETH Relay 8CH",
    16: "Modbus POE ETH Relay 16CH",
    30: "Modbus POE ETH Relay 30CH",
}
DEFAULT_RELAY_NAMES = [
    f"Relais {i}" for i in range(1, max(SUPPORTED_RELAY_COUNTS) + 1)
]

# Services
SERVICE_START_TEST = "funktionstest_start"
SERVICE_STOP_TEST = "funktionstest_stop"
SERVICE_RESET_STATS = "statistik_zuruecksetzen"
SERVICE_ALL_OFF = "alle_aus"

# Attribute keys
ATTR_ON_DURATION = "einschaltdauer_s"
ATTR_OFF_DURATION = "ausschaltdauer_s"


def model_name_for_relay_count(relay_count: int) -> str:
    """Human-readable Waveshare model name for the configured relay count."""
    return RELAY_COUNT_MODELS.get(relay_count, f"Modbus POE ETH Relay {relay_count}CH")
