"""Konstanten für die Waveshare PoE Relay Integration."""

DOMAIN = "waveshare_relay"
VERSION = "1.0.5"

# Config keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_UNIT_ID = "unit_id"
CONF_POLL_INTERVAL = "poll_interval"
CONF_RELAY_NAMES = "relay_names"

# Defaults
DEFAULT_PORT = 502
DEFAULT_UNIT_ID = 1
DEFAULT_POLL_INTERVAL = 2
DEFAULT_RELAY_NAMES = [f"Relais {i}" for i in range(1, 9)]
NUM_RELAYS = 8

# Services
SERVICE_START_TEST = "funktionstest_start"
SERVICE_STOP_TEST = "funktionstest_stop"
SERVICE_RESET_STATS = "statistik_zuruecksetzen"
SERVICE_ALL_OFF = "alle_aus"

# Attribute keys
ATTR_ON_DURATION = "einschaltdauer_s"
ATTR_OFF_DURATION = "ausschaltdauer_s"
