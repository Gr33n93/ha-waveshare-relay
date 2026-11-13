"""Shared entity base: device info and per-channel entities."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, model_name_for_relay_count
from .coordinator import WaveshareRelayCoordinator


def device_info(
    entry: ConfigEntry, coordinator: WaveshareRelayCoordinator
) -> DeviceInfo:
    """Device info for all entities of a board (single definition)."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=f"Waveshare Relay ({entry.data.get('host', '?')})",
        manufacturer="Waveshare / ZLAN",
        model=model_name_for_relay_count(coordinator.relay_count),
        configuration_url="https://github.com/Gr33n93/ha-waveshare-relay",
    )


class WaveshareChannelEntity(
    CoordinatorEntity[WaveshareRelayCoordinator]
):
    """Base for entities that represent exactly one channel.

    Wires up unique_id and device info; the friendly name is read
    dynamically from the channel profile so renames and mode changes
    apply instantly without a reload.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
        *,
        unique_id: str,
        translation_key: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._attr_translation_key = translation_key
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info(entry, coordinator)

    @property
    def name(self) -> str | None:
        """Friendly name: channel name plus optional suffix."""
        base = self.coordinator.relay_names[self._channel]
        if not self.translation_key or not self.platform_data:
            return base
        key = (
            f"component.{DOMAIN}.entity.{self.platform_data.domain}."
            f"{self.translation_key}.name"
        )
        template = self.platform_data.platform_translations.get(key, "{channel}")
        return template.format(channel=base)
