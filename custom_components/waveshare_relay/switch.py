"""Switch platform: relays as HA switches."""
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
    """Create switch entities."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WaveshareRelaySwitch(coordinator, entry, channel)
        for channel in range(coordinator.relay_count)
    )


class WaveshareRelaySwitch(WaveshareChannelEntity, SwitchEntity):
    """A single relay switch."""

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
    ) -> None:
        """Initialize the switch."""
        super().__init__(
            coordinator,
            entry,
            channel,
            unique_id=f"{entry.entry_id}_relay_{channel + 1}",
        )

    @property
    def _config(self):
        """Current channel profile (mode, name, pulse duration)."""
        return self.coordinator.channel_configs[self._channel]

    @property
    def icon(self) -> str:
        """Icon depending on the channel mode."""
        if self._config.mode == ChannelMode.PULSE:
            return "mdi:gesture-tap-button"
        return "mdi:electric-switch"

    @property
    def is_on(self) -> bool:
        """Current relay state."""
        return self.coordinator.relay_states[self._channel]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Extra attributes: durations, counters, mode.

        Deliberately the frozen values (as of the last relay change)
        instead of the live calculation - attribute changes on every
        poll would flood the recorder.
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
        """Continuous mode: switch on. Pulse mode: trigger native pulse."""
        config = self._config
        if config.mode == ChannelMode.PULSE:
            await self.coordinator.async_pulse(
                self._channel, config.pulse_duration_ms, "HA-UI"
            )
        else:
            await self.coordinator.async_write_coil(self._channel, True, "HA-UI")
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Switch off; also safely ends a running pulse."""
        await self.coordinator.async_write_coil(self._channel, False, "HA-UI")
        self.async_write_ha_state()
