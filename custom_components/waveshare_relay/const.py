"""Constants for the Waveshare PoE relay integration."""

DOMAIN = "waveshare_relay"

# Config keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_POLL_INTERVAL = "poll_interval"
CONF_RELAY_COUNT = "relay_count"
CONF_CHANNEL_CONFIGS = "channel_configs"

# Options flow field keys
CONF_CHANNEL = "channel"
CONF_CHANNEL_NAME = "channel_name"
CONF_CHANNEL_MODE = "betriebsart"
CONF_PULSE_DURATION = "impulsdauer_ms"

# Channel modes (values stored in entry.options[CONF_CHANNEL_CONFIGS])
MODE_SWITCH = "switch"  # continuous operation
MODE_PULSE = "pulse"  # momentary pulse

# Pulse duration limits (Waveshare time resolution: 100 ms)
DEFAULT_PULSE_DURATION_MS = 500
MIN_PULSE_DURATION_MS = 100
MAX_PULSE_DURATION_MS = 10000
PULSE_STEP_MS = 100

# Waveshare native pulse addresses (FC05, value = time in 100 ms ticks)
PULSE_ADDR_ON = 0x0200
PULSE_ADDR_OFF = 0x0400

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

# Services
SERVICE_START_TEST = "funktionstest_start"
SERVICE_STOP_TEST = "funktionstest_stop"
SERVICE_RESET_STATS = "statistik_zuruecksetzen"
SERVICE_ALL_OFF = "alle_aus"

# Attribute keys
ATTR_ON_DURATION = "einschaltdauer_s"
ATTR_OFF_DURATION = "ausschaltdauer_s"
ATTR_LAST_PULSE = "letzter_impuls"


def model_name_for_relay_count(relay_count: int) -> str:
    """Human-readable Waveshare model name for the configured relay count."""
    return RELAY_COUNT_MODELS.get(relay_count, f"Modbus POE ETH Relay {relay_count}CH")
