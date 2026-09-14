"""Sensor platform: statistics sensors for the Waveshare relay."""
from __future__ import annotations

import logging
import time
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WaveshareRelayCoordinator
from .entity import WaveshareChannelEntity, device_info

_LOGGER = logging.getLogger(__name__)

# These values change on every poll (2 s). To keep them from flooding
# logbook and recorder they write their state at most once per minute.
CHURN_UPDATE_INTERVAL = 60
CHURNY_KEYS = {
    "abfragen_gesamt",
    "abfragen_ok",
    "letzte_abfrage_ms",
    "schreibvorgaenge_gesamt",
    "schreiben_ok",
    "letzter_erfolg_zeit",
}

# Board-wide statistics sensors
GLOBAL_SENSORS: list[dict[str, Any]] = [
    {"key": "abfragen_gesamt",       "name": "Abfragen gesamt",           "icon": "mdi:counter",        "unit": None, "cls": SensorStateClass.TOTAL_INCREASING},
    {"key": "abfragen_ok",           "name": "Abfragen erfolgreich",      "icon": "mdi:check-circle",   "unit": None, "cls": SensorStateClass.TOTAL_INCREASING},
    {"key": "abfragen_fehler",       "name": "Abfragen fehlgeschlagen",   "icon": "mdi:alert-circle",   "unit": None, "cls": SensorStateClass.TOTAL_INCREASING},
    {"key": "letzte_abfrage_ms",     "name": "Reaktionszeit",             "icon": "mdi:timer",          "unit": "ms", "cls": SensorStateClass.MEASUREMENT},
    {"key": "schreibvorgaenge_gesamt","name": "Schreibvorgänge gesamt",   "icon": "mdi:pencil",         "unit": None, "cls": SensorStateClass.TOTAL_INCREASING},
    {"key": "schreiben_ok",          "name": "Schreiben erfolgreich",     "icon": "mdi:check",          "unit": None, "cls": SensorStateClass.TOTAL_INCREASING},
    {"key": "schreiben_fehler",      "name": "Schreiben fehlgeschlagen",  "icon": "mdi:alert",          "unit": None, "cls": SensorStateClass.TOTAL_INCREASING},
    {"key": "letzte_fehlermeldung",  "name": "Letzte Fehlermeldung",      "icon": "mdi:message-alert",  "unit": None, "cls": None},
    {"key": "letzter_fehler_zeit",   "name": "Letzter Fehler (Zeit)",     "icon": "mdi:clock-alert",    "unit": None, "cls": None},
    {"key": "letzter_erfolg_zeit",   "name": "Letzter Erfolg (Zeit)",     "icon": "mdi:clock-check",    "unit": None, "cls": None},
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create sensor entities."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    # Board-wide statistics
    for sd in GLOBAL_SENSORS:
        entities.append(WaveshareGlobalSensor(coordinator, entry, sd))

    # Function test status
    entities.append(WaveshareTestStatusSensor(coordinator, entry))

    # Per channel: on/off duration, counters
    for ch in range(coordinator.relay_count):
        entities.append(WaveshareChannelDurationSensor(coordinator, entry, ch, "ein"))
        entities.append(WaveshareChannelDurationSensor(coordinator, entry, ch, "aus"))
        entities.append(WaveshareChannelCounterSensor(coordinator, entry, ch, "ein"))
        entities.append(WaveshareChannelCounterSensor(coordinator, entry, ch, "aus"))
        entities.append(WaveshareChannelCounterSensor(coordinator, entry, ch, "fehler"))

    async_add_entities(entities)


class WaveshareGlobalSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], SensorEntity
):
    """Board-wide statistics sensor."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, sdef: dict) -> None:
        super().__init__(coordinator)
        self._key = sdef["key"]
        self._last_write = 0.0
        self._attr_unique_id = f"{entry.entry_id}_stat_{self._key}"
        self._attr_name = sdef["name"]
        self._attr_icon = sdef["icon"]
        self._attr_native_unit_of_measurement = sdef["unit"]
        self._attr_state_class = sdef["cls"]
        self._attr_device_info = device_info(entry, coordinator)

    @property
    def native_value(self) -> Any:
        return self.coordinator.stats.get(self._key, 0)

    @callback
    def _handle_coordinator_update(self) -> None:
        if self._key in CHURNY_KEYS:
            now = time.monotonic()
            if now - self._last_write < CHURN_UPDATE_INTERVAL:
                return
            self._last_write = now
        self.async_write_ha_state()


class WaveshareTestStatusSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], SensorEntity
):
    """Function test status sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:test-tube"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_test_status"
        self._attr_name = "Funktionstest"
        self._attr_device_info = device_info(entry, coordinator)

    @property
    def native_value(self) -> str:
        if self.coordinator.test_running:
            ch = self.coordinator.test_current_channel
            return f"Läuft – Kanal {ch}"
        return "Inaktiv"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "laeuft": self.coordinator.test_running,
            "aktueller_kanal": self.coordinator.test_current_channel,
        }


class WaveshareChannelDurationSensor(WaveshareChannelEntity, SensorEntity):
    """On or off duration of one channel."""

    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, channel: int, kind: str) -> None:
        super().__init__(
            coordinator,
            entry,
            channel,
            unique_id=f"{entry.entry_id}_ch{channel + 1}_{kind}_dauer",
            name_suffix="Einschaltdauer" if kind == "ein" else "Ausschaltdauer",
        )
        self._kind = kind  # "ein" or "aus"
        self._last_write = 0.0
        self._last_written_val: float | None = None
        self._attr_icon = "mdi:timer-play" if kind == "ein" else "mdi:timer-pause"

    @property
    def native_value(self) -> float:
        """Cumulative seconds as of the last relay change.

        Deliberately without live progression - otherwise the state
        would change on every poll and flood logbook and recorder. The
        current live value is exposed as attribute `aktuell_s`.
        """
        return self.coordinator.channel_stats[self._channel][
            f"{self._kind}schaltdauer_s"
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        live = self.coordinator.get_channel_stats(self._channel)[
            f"{self._kind}schaltdauer_s"
        ]
        return {"aktuell_s": live}

    @callback
    def _handle_coordinator_update(self) -> None:
        # Write immediately when the frozen value changes (relay toggle);
        # otherwise throttle the attribute refresh to once per minute,
        # because even attribute-only changes create recorder rows.
        val = self.coordinator.channel_stats[self._channel][
            f"{self._kind}schaltdauer_s"
        ]
        now = time.monotonic()
        if val == self._last_written_val and (
            now - self._last_write < CHURN_UPDATE_INTERVAL
        ):
            return
        self._last_written_val = val
        self._last_write = now
        self.async_write_ha_state()


class WaveshareChannelCounterSensor(WaveshareChannelEntity, SensorEntity):
    """Counters per channel (on/off/errors)."""

    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    _LABELS = {"ein": "EIN-Zähler", "aus": "AUS-Zähler", "fehler": "Schreibfehler"}
    _ICONS = {
        "ein": "mdi:toggle-switch",
        "aus": "mdi:toggle-switch-off",
        "fehler": "mdi:alert-octagon",
    }
    _STAT_KEYS = {"ein": "ein_zaehler", "aus": "aus_zaehler", "fehler": "schreibfehler"}

    def __init__(self, coordinator, entry, channel: int, kind: str) -> None:
        super().__init__(
            coordinator,
            entry,
            channel,
            unique_id=f"{entry.entry_id}_ch{channel + 1}_{kind}_cnt",
            name_suffix=self._LABELS[kind],
        )
        self._stat_key = self._STAT_KEYS[kind]
        self._attr_icon = self._ICONS[kind]

    @property
    def native_value(self) -> int:
        return self.coordinator.channel_stats[self._channel].get(self._stat_key, 0)
