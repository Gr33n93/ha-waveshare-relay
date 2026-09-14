"""Binary sensor: connection status of the relay board."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WaveshareRelayCoordinator
from .entity import device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the connection binary sensor."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WaveshareConnectionSensor(coordinator, entry)])


class WaveshareConnectionSensor(
    CoordinatorEntity[WaveshareRelayCoordinator], BinarySensorEntity
):
    """Connection status of the relay board."""

    _attr_has_entity_name = True
    _attr_name = "Verbindung"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_icon = "mdi:lan-connect"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_connection"
        self._attr_device_info = device_info(entry, coordinator)

    @property
    def is_on(self) -> bool:
        """Connected when the last poll succeeded."""
        return self.coordinator.last_update_success
