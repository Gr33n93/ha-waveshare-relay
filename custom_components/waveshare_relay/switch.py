"""Switch-Plattform: Relais als HA-Switches."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_LAST_PULSE,
    ATTR_ON_DURATION,
    ATTR_OFF_DURATION,
    DOMAIN,
)
from .coordinator import WaveshareRelayCoordinator
from .entity import WaveshareChannelEntity
from .models import ChannelMode

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Switch-Entities anlegen."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WaveshareRelaySwitch(coordinator, entry, channel)
        for channel in range(coordinator.relay_count)
    )


class WaveshareRelaySwitch(WaveshareChannelEntity, SwitchEntity):
    """Ein einzelner Relais-Schalter."""

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
    ) -> None:
        """Initialisierung."""
        super().__init__(
            coordinator,
            entry,
            channel,
            unique_id=f"{entry.entry_id}_relay_{channel + 1}",
        )

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
    def extra_state_attributes(self) -> dict[str, Any]:
        """Zusatzattribute: Dauer, Zähler, Betriebsart.

        Bewusst die eingefrorenen Werte (Stand: letzter Wechsel) statt der
        Live-Berechnung – Attribut-Änderungen bei jedem Poll würden den
        Recorder fluten.
        """
        cs = self.coordinator.channel_stats[self._channel]
        config = self._config
        attrs: dict[str, Any] = {
            ATTR_ON_DURATION: cs["einschaltdauer_s"],
            ATTR_OFF_DURATION: cs["ausschaltdauer_s"],
            "ein_zaehler": cs["ein_zaehler"],
            "aus_zaehler": cs["aus_zaehler"],
            "schreibfehler": cs["schreibfehler"],
            "letzter_befehl": cs["letzter_befehl"],
            "betriebsart": "pulse" if config.mode == ChannelMode.PULSE else "switch",
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
