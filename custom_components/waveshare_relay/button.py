"""Button-Plattform: Funktionstest, Alle Aus, Statistik Reset."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WaveshareRelayCoordinator
from .entity import device_info

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


class _WaveshareButton(CoordinatorEntity[WaveshareRelayCoordinator], ButtonEntity):
    """Gemeinsame Basis der Board-Buttons (unique_id, Geräte-Info)."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, id_suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{id_suffix}"
        self._attr_device_info = device_info(entry, coordinator)


class WaveshareTestStartButton(_WaveshareButton):
    """Funktionstest starten."""

    _attr_name = "Funktionstest starten"
    _attr_icon = "mdi:play-circle"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "test_start")

    async def async_press(self) -> None:
        await self.coordinator.async_start_test(
            laufzeit_s=5.0, pause_s=0.25, einmalig=True
        )


class WaveshareTestStopButton(_WaveshareButton):
    """Funktionstest stoppen."""

    _attr_name = "Funktionstest stoppen"
    _attr_icon = "mdi:stop-circle"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "test_stop")

    async def async_press(self) -> None:
        await self.coordinator.async_stop_test()


class WaveshareAllOffButton(_WaveshareButton):
    """Alle Relais ausschalten."""

    _attr_name = "Alle Relais aus"
    _attr_icon = "mdi:power-off"

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "all_off")

    async def async_press(self) -> None:
        await self.coordinator.async_all_off()


class WaveshareResetStatsButton(_WaveshareButton):
    """Statistik zurücksetzen."""

    _attr_name = "Statistik zurücksetzen"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator, entry, "reset_stats")

    async def async_press(self) -> None:
        self.coordinator.reset_stats()
