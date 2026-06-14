"""Waveshare PoE Ethernet Relay (8CH) – Home Assistant Integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DOMAIN,
    CONF_UNIT_ID,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    SERVICE_START_TEST,
    SERVICE_STOP_TEST,
    SERVICE_RESET_STATS,
    SERVICE_ALL_OFF,
)
from .coordinator import WaveshareRelayCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

SERVICE_TEST_SCHEMA = vol.Schema(
    {
        vol.Optional("laufzeit_s", default=5.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.1, max=300)
        ),
        vol.Optional("pause_s", default=0.25): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=60)
        ),
        vol.Optional("einmalig", default=True): bool,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration einrichten wenn Config Entry geladen wird."""
    hass.data.setdefault(DOMAIN, {})

    coordinator = WaveshareRelayCoordinator(
        hass=hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        unit_id=entry.data[CONF_UNIT_ID],
        poll_interval=entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services nur einmal global registrieren (wirken auf alle Geräte)
    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration entladen."""
    coordinator: WaveshareRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    await coordinator.async_shutdown()

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)

    # Services entfernen wenn kein Gerät mehr übrig
    if not hass.data[DOMAIN]:
        for svc in (SERVICE_START_TEST, SERVICE_STOP_TEST, SERVICE_RESET_STATS, SERVICE_ALL_OFF):
            hass.services.async_remove(DOMAIN, svc)

    return unloaded


def _get_all_coordinators(hass: HomeAssistant) -> list[WaveshareRelayCoordinator]:
    """Alle aktiven Coordinators zurückgeben."""
    return list(hass.data.get(DOMAIN, {}).values())


def _register_services(hass: HomeAssistant) -> None:
    """Services registrieren (wirken auf alle verbundenen Geräte)."""

    if hass.services.has_service(DOMAIN, SERVICE_START_TEST):
        return  # Bereits registriert

    async def handle_start_test(call: ServiceCall) -> None:
        for coord in _get_all_coordinators(hass):
            await coord.async_start_test(
                laufzeit_s=call.data.get("laufzeit_s", 5.0),
                pause_s=call.data.get("pause_s", 0.25),
                einmalig=call.data.get("einmalig", True),
            )

    async def handle_stop_test(call: ServiceCall) -> None:
        for coord in _get_all_coordinators(hass):
            await coord.async_stop_test()

    async def handle_reset_stats(call: ServiceCall) -> None:
        for coord in _get_all_coordinators(hass):
            coord.reset_stats()

    async def handle_all_off(call: ServiceCall) -> None:
        for coord in _get_all_coordinators(hass):
            await coord.async_all_off()

    hass.services.async_register(
        DOMAIN, SERVICE_START_TEST, handle_start_test, schema=SERVICE_TEST_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_TEST, handle_stop_test)
    hass.services.async_register(DOMAIN, SERVICE_RESET_STATS, handle_reset_stats)
    hass.services.async_register(DOMAIN, SERVICE_ALL_OFF, handle_all_off)

    _LOGGER.info("Waveshare Relay Services registriert")
