"""Gemeinsame Entity-Basis: Geräte-Info und Kanal-Entities."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, model_name_for_relay_count
from .coordinator import WaveshareRelayCoordinator


def device_info(
    entry: ConfigEntry, coordinator: WaveshareRelayCoordinator
) -> DeviceInfo:
    """Geräte-Info für alle Entities dieses Boards (einzige Definition)."""
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
    """Basis für Entities, die genau einen Kanal abbilden.

    Verdrahtet unique_id und Geräte-Info einheitlich; der Anzeigename
    wird dynamisch aus dem Kanalprofil gelesen, sodass Umbenennungen und
    Moduswechsel ohne Reload sofort greifen.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WaveshareRelayCoordinator,
        entry: ConfigEntry,
        channel: int,
        *,
        unique_id: str,
        name_suffix: str = "",
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        self._name_suffix = name_suffix
        self._attr_unique_id = unique_id
        self._attr_device_info = device_info(entry, coordinator)

    @property
    def name(self) -> str | None:
        """Anzeigename: Kanalname plus optionalem Suffix."""
        base = self.coordinator.relay_names[self._channel]
        return f"{base} {self._name_suffix}" if self._name_suffix else base
