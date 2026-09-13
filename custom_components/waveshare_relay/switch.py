"""Switch-Plattform: Relais als HA-Switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_LAST_PULSE,
    ATTR_ON_DURATION,
    ATTR_OFF_DURATION,
    DOMAIN,
    model_name_for_relay_count,
)
from .coordinator import WaveshareRelayCoordinator
from .models import ChannelMode

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Switch-Entities anlegen."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        WaveshareRelaySwitch(coordinator, entry, channel)
        for channel in range(coordinator.relay_count)
    ]
    async_add_entities(entities)


class WaveshareRelaySwitch(CoordinatorEntity[WaveshareRelayCoordinator], SwitchEntity):
    """Ein einzelner Relais-Schalter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
    ) -> None:
        """Initialisierung."""
        super().__init__(coordinator)
        self._channel = channel
        self._attr_unique_id = f"{entry.entry_id}_relay_{channel + 1}"
        self._attr_name = coordinator.relay_names[channel]
        self._attr_device_info = _device_info(entry, coordinator)

    @property
    def _config(self):
        """Aktuelles Kanalprofil (Betriebsart, Name, Impulsdauer)."""
        return self.coordinator.channel_configs[self._channel]

    @property
    def icon(self) -> str:
        """Icon je Betriebsart."""
        if self._config.mode == ChannelMode.PULSE:
            return "mdi:gesture-tap-button"
        return "mdi:electric-switch"

    @property
    def is_on(self) -> bool:
        """Aktueller Zustand."""
        return self.coordinator.relay_states[self._channel]

    @property
    def available(self) -> bool:
        """Verfügbar wenn Verbindung steht."""
        return self.coordinator.stats.get("verbunden", False)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusatzattribute: Dauer, Zähler, Betriebsart."""
        cs = self.coordinator.get_channel_stats(self._channel)
        config = self._config
        attrs: dict[str, Any] = {
            ATTR_ON_DURATION: cs["einschaltdauer_s"],
            ATTR_OFF_DURATION: cs["ausschaltdauer_s"],
            "ein_zaehler": cs["ein_zaehler"],
            "aus_zaehler": cs["aus_zaehler"],
            "schreibfehler": cs["schreibfehler"],
            "letzter_befehl": cs["letzter_befehl"],
            "betriebsart": "impuls" if config.mode == ChannelMode.PULSE else "dauerbetrieb",
        }
        if config.mode == ChannelMode.PULSE:
            attrs["impulsdauer_ms"] = config.pulse_duration_ms
            attrs[ATTR_LAST_PULSE] = cs["letzter_impuls"]
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Dauerbetrieb: einschalten. Impuls: nativen Impuls auslösen."""
        config = self._config
        if config.mode == ChannelMode.PULSE:
            await self.coordinator.async_pulse(
                self._channel, config.pulse_duration_ms, "HA-UI"
            )
        else:
            await self.coordinator.async_write_coil(self._channel, True, "HA-UI")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Ausschalten; beendet auch einen laufenden Impuls."""
        await self.coordinator.async_write_coil(self._channel, False, "HA-UI")
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Coordinator-Update verarbeiten."""
        self.async_write_ha_state()


def _device_info(entry: ConfigEntry, coordinator: WaveshareRelayCoordinator) -> dict:
    """Geräte-Info für alle Entities dieses Boards."""
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": f"Waveshare Relay ({entry.data.get('host', '?')})",
        "manufacturer": "Waveshare / ZLAN",
        "model": model_name_for_relay_count(coordinator.relay_count),
        "configuration_url": "https://github.com/Gr33n93/ha-waveshare-relay",
    }
