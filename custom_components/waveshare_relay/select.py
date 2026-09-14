"""Select platform: per-channel mode (Switch/Pulse).

Every channel gets a mode select that is enabled by default and sits in
the device control section right next to the relay switches - the same
mechanism as the options dialog.
"""
from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CHANNEL_CONFIGS,
    DEFAULT_PULSE_DURATION_MS,
    DOMAIN,
)
from .coordinator import WaveshareRelayCoordinator
from .entity import WaveshareChannelEntity
from .models import ChannelMode

_LOGGER = logging.getLogger(__name__)

# Display labels -> canonical mode (stored value stays switch/pulse)
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
    """Create mode selects (enabled by default)."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        WaveshareChannelModeSelect(coordinator, entry, channel)
        for channel in range(coordinator.relay_count)
    ]
    _LOGGER.info("Select platform: created %d mode selects", len(entities))
    async_add_entities(entities)


class WaveshareChannelModeSelect(WaveshareChannelEntity, SelectEntity):
    """Mode of one channel: Switch (continuous) or Pulse (momentary)."""

    _attr_icon = "mdi:tune-variant"

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
    ) -> None:
        super().__init__(
            coordinator,
            entry,
            channel,
            unique_id=f"{entry.entry_id}_relay_{channel + 1}_mode",
            name_suffix="Mode",
        )
        self._entry = entry

    @property
    def options(self) -> list[str]:
        """Selectable modes."""
        return list(MODE_LABELS)

    @property
    def current_option(self) -> str:
        """Currently selected mode."""
        mode = self.coordinator.channel_configs[self._channel].mode
        return MODE_TO_LABEL[mode]

    async def async_select_option(self, option: str) -> None:
        """Change the mode and persist it in the entry options."""
        mode = MODE_LABELS[option]
        config = self.coordinator.channel_configs[self._channel]
        if config.mode == mode:
            return

        config.mode = mode

        # Persist: the update listener feeds the new profile into the
        # running coordinator, so switches pick up the new behaviour
        # instantly (entity IDs stay the same).
        stored = dict(self._entry.options.get(CONF_CHANNEL_CONFIGS, {}))
        item = dict(stored.get(str(self._channel), {}))
        item.setdefault("name", config.name)
        item.setdefault(
            "pulse_duration_ms", config.pulse_duration_ms or DEFAULT_PULSE_DURATION_MS
        )
        item["mode"] = str(mode)
        stored[str(self._channel)] = item
        options = dict(self._entry.options)
        options[CONF_CHANNEL_CONFIGS] = stored
        self.hass.config_entries.async_update_entry(self._entry, options=options)

        _LOGGER.info("Channel %d mode set to %s", self._channel + 1, option)
