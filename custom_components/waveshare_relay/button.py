"""Button-Plattform: Funktionstest, Alle Aus, Statistik Reset."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import WaveshareRelayCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Button-Entities anlegen."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            WaveshareTestStartButton(coordinator, entry),
            WaveshareTestStopButton(coordinator, entry),
            WaveshareAllOffButton(coordinator, entry),
            WaveshareResetStatsButton(coordinator, entry),
        ],
    )


def _device_info(entry: ConfigEntry) -> dict:
    return {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": f"Waveshare Relay ({entry.data.get('host', '?')})",
        "manufacturer": "Waveshare / ZLAN",
        "model": "PoE ETH Relay 8CH",
        "sw_version": VERSION,
        "configuration_url": "https://github.com/Gr33n93/ha-waveshare-relay",
    }


class WaveshareTestStartButton(
    CoordinatorEntity[WaveshareRelayCoordinator], ButtonEntity
):
    """Funktionstest starten."""

    _attr_has_entity_name = True
    _attr_name = "Funktionstest starten"
    _attr_icon = "mdi:play-circle"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_test_start"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        await self.coordinator.async_start_test(
            laufzeit_s=5.0, pause_s=0.25, einmalig=True
        )


class WaveshareTestStopButton(
    CoordinatorEntity[WaveshareRelayCoordinator], ButtonEntity
):
    """Funktionstest stoppen."""

    _attr_has_entity_name = True
    _attr_name = "Funktionstest stoppen"
    _attr_icon = "mdi:stop-circle"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_test_stop"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        await self.coordinator.async_stop_test()


class WaveshareAllOffButton(
    CoordinatorEntity[WaveshareRelayCoordinator], ButtonEntity
):
    """Alle Relais ausschalten."""

    _attr_has_entity_name = True
    _attr_name = "Alle Relais aus"
    _attr_icon = "mdi:power-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_all_off"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        await self.coordinator.async_all_off()


class WaveshareResetStatsButton(
    CoordinatorEntity[WaveshareRelayCoordinator], ButtonEntity
):
    """Statistik zurücksetzen."""

    _attr_has_entity_name = True
    _attr_name = "Statistik zurücksetzen"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_reset_stats"
        self._attr_device_info = _device_info(entry)

    async def async_press(self) -> None:
        self.coordinator.reset_stats()
