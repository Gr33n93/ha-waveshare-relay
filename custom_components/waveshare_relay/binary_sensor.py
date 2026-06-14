"""Binary Sensor: Verbindungsstatus zum Relay-Board."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import WaveshareRelayCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary Sensor anlegen."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [WaveshareConnectionSensor(coordinator, entry)]
    )


class WaveshareConnectionSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], BinarySensorEntity
):
    """Verbindungsstatus zum Relay-Board."""

    _attr_has_entity_name = True
    _attr_name = "Verbindung"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:lan-connect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connection"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Waveshare Relay ({entry.data.get('host', '?')})",
            "manufacturer": "Waveshare / ZLAN",
            "model": "PoE ETH Relay 8CH",
            "sw_version": VERSION,
        "configuration_url": "https://github.com/Gr33n93/ha-waveshare-relay",
        }

    @property
    def is_on(self) -> bool:
        """True wenn verbunden."""
        return self.coordinator.stats.get("verbunden", False)

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
