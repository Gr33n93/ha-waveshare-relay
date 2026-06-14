"""Sensor-Plattform: Statistik-Sensoren für Waveshare Relay."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION, model_name_for_relay_count
from .coordinator import WaveshareRelayCoordinator

_LOGGER = logging.getLogger(__name__)

# ── Globale Statistik-Sensoren ──
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
    """Sensor-Entities anlegen."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    # Globale Statistik
    for sd in GLOBAL_SENSORS:
        entities.append(WaveshareGlobalSensor(coordinator, entry, sd))

    # Funktionstest-Status
    entities.append(WaveshareTestStatusSensor(coordinator, entry))

    # Pro-Kanal: EIN-Dauer, AUS-Dauer, Zähler
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
    """Globaler Statistik-Sensor."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, sdef: dict) -> None:
        super().__init__(coordinator)
        self._key = sdef["key"]
        self._attr_unique_id = f"{entry.entry_id}_stat_{self._key}"
        self._attr_name = sdef["name"]
        self._attr_icon = sdef["icon"]
        self._attr_native_unit_of_measurement = sdef["unit"]
        self._attr_state_class = sdef["cls"]
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def native_value(self) -> Any:
        return self.coordinator.stats.get(self._key, 0)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class WaveshareTestStatusSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], SensorEntity
):
    """Funktionstest-Status Sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:test-tube"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_test_status"
        self._attr_name = "Funktionstest"
        self._attr_device_info = _device_info(entry, coordinator)

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

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class WaveshareChannelDurationSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], SensorEntity
):
    """Einschalt- oder Ausschaltdauer pro Kanal."""

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "s"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, channel: int, kind: str) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._kind = kind  # "ein" or "aus"
        label = "Einschaltdauer" if kind == "ein" else "Ausschaltdauer"
        self._attr_unique_id = f"{entry.entry_id}_ch{channel + 1}_{kind}_dauer"
        self._attr_name = f"Relais {channel + 1} {label}"
        self._attr_icon = "mdi:timer-play" if kind == "ein" else "mdi:timer-pause"
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def native_value(self) -> float:
        cs = self.coordinator.get_channel_stats(self._channel)
        return cs[f"{self._kind}schaltdauer_s"]

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


class WaveshareChannelCounterSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], SensorEntity
):
    """Zähler pro Kanal (EIN/AUS/Fehler)."""

    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, channel: int, kind: str) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._kind = kind
        labels = {"ein": "EIN-Zähler", "aus": "AUS-Zähler", "fehler": "Schreibfehler"}
        icons = {"ein": "mdi:toggle-switch", "aus": "mdi:toggle-switch-off", "fehler": "mdi:alert-octagon"}
        keys = {"ein": "ein_zaehler", "aus": "aus_zaehler", "fehler": "schreibfehler"}
        self._stat_key = keys[kind]
        self._attr_unique_id = f"{entry.entry_id}_ch{channel + 1}_{kind}_cnt"
        self._attr_name = f"Relais {channel + 1} {labels[kind]}"
        self._attr_icon = icons[kind]
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def native_value(self) -> int:
        return self.coordinator.channel_stats[self._channel].get(self._stat_key, 0)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


def _device_info(entry: ConfigEntry, coordinator: WaveshareRelayCoordinator) -> dict:
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": f"Waveshare Relay ({entry.data.get('host', '?')})",
        "manufacturer": "Waveshare / ZLAN",
        "model": model_name_for_relay_count(coordinator.relay_count),
        "sw_version": VERSION,
        "configuration_url": "https://github.com/Gr33n93/ha-waveshare-relay",
    }
