"""Waveshare Modbus PoE Ethernet Relay Home Assistant Integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    CONF_UNIT_ID,
    CONF_POLL_INTERVAL,
    CONF_RELAY_COUNT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RELAY_COUNT,
    SERVICE_START_TEST,
    SERVICE_STOP_TEST,
    SERVICE_RESET_STATS,
    SERVICE_ALL_OFF,
)
from .coordinator import WaveshareRelayCoordinator
from .models import channel_configs_from_entry

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SELECT,
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
        # Ohne diesen Key verwirft voluptuous die Geräteauswahl und der
        # Aufruf fehlschlaegt mit "extra keys not allowed".
        vol.Optional("device_id"): str,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Integration einrichten wenn Config Entry geladen wird."""
    hass.data.setdefault(DOMAIN, {})

    # Releases up to 1.1.5 stored the integration version as device firmware.
    # Clear that stale value because the relay does not report its firmware.
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    if device is not None and device.sw_version is not None:
        device_registry.async_update_device(device.id, sw_version=None)

    relay_count = entry.data.get(CONF_RELAY_COUNT, DEFAULT_RELAY_COUNT)
    coordinator = WaveshareRelayCoordinator(
        hass=hass,
        host=entry.data[CONF_HOST],
        port=entry.data[CONF_PORT],
        unit_id=entry.data[CONF_UNIT_ID],
        poll_interval=entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
        relay_count=relay_count,
        channel_configs=channel_configs_from_entry(entry.options, relay_count),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Services nur einmal global registrieren (Ziel optional wählbar)
    _register_services(hass)

    # Optionsänderungen (Kanalprofile) laden den Entry neu
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Entry bei geänderten Optionen neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)


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


def _resolve_coordinators(
    hass: HomeAssistant, call: ServiceCall
) -> list[WaveshareRelayCoordinator]:
    """Coordinators des Aufrufs ermitteln: Zielgerät oder alle Boards."""
    device_id = call.data.get("device_id")
    if not device_id:
        return _get_all_coordinators(hass)

    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise HomeAssistantError(f"Gerät {device_id} nicht gefunden")

    coordinators: list[WaveshareRelayCoordinator] = []
    for entry_id in device.config_entries:
        coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
        if isinstance(coordinator, WaveshareRelayCoordinator):
            coordinators.append(coordinator)
    if not coordinators:
        raise HomeAssistantError(
            "Das gewählte Gerät gehört zu keiner aktiven Waveshare-Instanz"
        )
    return coordinators


def _register_services(hass: HomeAssistant) -> None:
    """Services registrieren (ohne Ziel: alle Geräte, mit Ziel: nur dieses)."""

    if hass.services.has_service(DOMAIN, SERVICE_START_TEST):
        return  # Bereits registriert

    async def handle_start_test(call: ServiceCall) -> None:
        for coord in _resolve_coordinators(hass, call):
            await coord.async_start_test(
                laufzeit_s=call.data.get("laufzeit_s", 5.0),
                pause_s=call.data.get("pause_s", 0.25),
                einmalig=call.data.get("einmalig", True),
            )

    async def handle_stop_test(call: ServiceCall) -> None:
        for coord in _resolve_coordinators(hass, call):
            await coord.async_stop_test()

    async def handle_reset_stats(call: ServiceCall) -> None:
        for coord in _resolve_coordinators(hass, call):
            coord.reset_stats()

    async def handle_all_off(call: ServiceCall) -> None:
        for coord in _resolve_coordinators(hass, call):
            await coord.async_all_off()

    hass.services.async_register(
        DOMAIN, SERVICE_START_TEST, handle_start_test, schema=SERVICE_TEST_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_STOP_TEST, handle_stop_test)
    hass.services.async_register(DOMAIN, SERVICE_RESET_STATS, handle_reset_stats)
    hass.services.async_register(DOMAIN, SERVICE_ALL_OFF, handle_all_off)

    _LOGGER.info("Waveshare Relay Services registriert")
