"""Select-Plattform: Betriebsart pro Kanal (Dauerbetrieb/Impuls).

Pro Kanal gibt es eine Betriebsart-Auswahl, die standardmäßig aktiv ist und
damit direkt am Gerät unter Steuerung sowie im Dashboard zur Verfügung steht –
derselbe Mechanismus wie im OptionsDialog.
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CHANNEL_CONFIGS,
    DEFAULT_PULSE_DURATION_MS,
    DOMAIN,
    model_name_for_relay_count,
)
from .coordinator import WaveshareRelayCoordinator
from .models import ChannelMode

_LOGGER = logging.getLogger(__name__)

# Anzeigetexte der Auswahl -> kanonischer Modus (gespeichert bleibt switch/pulse)
MODE_LABELS = {
    "Switch": ChannelMode.SWITCH,
    "Pulse": ChannelMode.PULSE,
}
MODE_TO_LABEL = {mode: label for label, mode in MODE_LABELS.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Betriebsart-Selects anlegen (standardmäßig aktiv)."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        WaveshareChannelModeSelect(coordinator, entry, channel)
        for channel in range(coordinator.relay_count)
    ]
    _LOGGER.info("Select-Plattform: %d Betriebsart-Selects angelegt", len(entities))
    async_add_entities(entities)


def _device_info(entry: ConfigEntry, coordinator: WaveshareRelayCoordinator) -> dict:
    """Geräte-Info für alle Entities dieses Boards."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": f"Waveshare Relay ({entry.data.get('host', '?')})",
        "manufacturer": "Waveshare / ZLAN",
        "model": model_name_for_relay_count(coordinator.relay_count),
        "configuration_url": "https://github.com/Gr33n93/ha-waveshare-relay",
    }


class WaveshareChannelModeSelect(
    CoordinatorEntity[WaveshareRelayCoordinator], SelectEntity
):
    """Betriebsart eines Kanals: Switch (Dauerbetrieb) oder Pulse (Impuls)."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:tune-variant"

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_relay_{channel + 1}_mode"
        self._attr_name = f"{coordinator.relay_names[channel]} Mode"
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def options(self) -> list[str]:
        """Wählbare Betriebsarten."""
        return list(MODE_LABELS)

    @property
    def available(self) -> bool:
        """Verfügbar wenn Verbindung steht."""
        return self.coordinator.stats.get("verbunden", False)

    @property
    def current_option(self) -> str:
        """Aktuell eingestellte Betriebsart."""
        mode = self.coordinator.channel_configs[self._channel].mode
        return MODE_TO_LABEL[mode]

    async def async_select_option(self, option: str) -> None:
        """Betriebsart umstellen und in den Entry-Optionen speichern."""
        mode = MODE_LABELS[option]
        config = self.coordinator.channel_configs[self._channel]
        if config.mode == mode:
            return

        config.mode = mode

        # Persistieren: der Update-Listener lädt den Entry neu, sodass die
        # Switch-Entity ihr Verhalten sofort übernimmt (ID bleibt gleich).
        stored = dict(self._entry.options.get(CONF_CHANNEL_CONFIGS, {}))
        item = dict(stored.get(str(self._channel), {}))
        item.setdefault("name", config.name)
        item.setdefault("pulse_duration_ms", config.pulse_duration_ms or DEFAULT_PULSE_DURATION_MS)
        item["mode"] = str(mode)
        stored[str(self._channel)] = item
        options = dict(self._entry.options)
        options[CONF_CHANNEL_CONFIGS] = stored
        self.hass.config_entries.async_update_entry(self._entry, options=options)

        _LOGGER.info(
            "Betriebsart Kanal %d auf %s gestellt", self._channel + 1, option
        )
