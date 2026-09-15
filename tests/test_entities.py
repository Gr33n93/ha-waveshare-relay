"""Tests for the entity platforms: identity, naming, throttling, persistence."""
from unittest.mock import AsyncMock, MagicMock, patch

import custom_components.waveshare_relay as pkg
from custom_components.waveshare_relay import entity as ent
from custom_components.waveshare_relay import select as select_mod
from custom_components.waveshare_relay import sensor as sensor_mod
from custom_components.waveshare_relay import switch as switch_mod
from custom_components.waveshare_relay.const import CONF_CHANNEL_CONFIGS
from custom_components.waveshare_relay.models import ChannelConfig, ChannelMode
from conftest import patch_ce


def make_coordinator_mock(names=("Garage", "Relais 2")):
    coordinator = MagicMock()
    coordinator.relay_names = list(names)
    coordinator.relay_count = len(names)
    coordinator.stats = {"verbunden": True}
    return coordinator


def test_channel_entity_identity_and_dynamic_names():
    coordinator = make_coordinator_mock()
    entry = MagicMock(entry_id="e1")
    with patch.object(ent.CoordinatorEntity, "__init__", patch_ce):
        switch = switch_mod.WaveshareRelaySwitch(coordinator, entry, 0)
        mode = select_mod.WaveshareChannelModeSelect(coordinator, entry, 0)
        duration = sensor_mod.WaveshareChannelDurationSensor(coordinator, entry, 1, "aus")
        counter = sensor_mod.WaveshareChannelCounterSensor(coordinator, entry, 0, "fehler")

    assert (switch.name, switch.unique_id) == ("Garage", "e1_relay_1")
    assert (mode.name, mode.unique_id) == ("Garage Mode", "e1_relay_1_mode")
    assert (duration.name, duration.unique_id) == ("Relais 2 Ausschaltdauer", "e1_ch2_aus_dauer")
    assert (counter.name, counter.unique_id) == ("Garage Schreibfehler", "e1_ch1_fehler_cnt")

    # Renaming a channel reaches the entities without rebuilding them.
    coordinator.relay_names[0] = "Werkbank"
    assert switch.name == "Werkbank"


async def test_switch_turn_on_branches_by_mode():
    coordinator = make_coordinator_mock(("A",))
    coordinator.async_pulse = AsyncMock()
    coordinator.async_write_coil = AsyncMock()
    coordinator.channel_configs = [ChannelConfig(channel=0, name="A", mode=ChannelMode.PULSE, pulse_duration_ms=600)]
    entry = MagicMock(entry_id="e1")
    with patch.object(ent.CoordinatorEntity, "__init__", patch_ce):
        switch = switch_mod.WaveshareRelaySwitch(coordinator, entry, 0)
    switch.async_write_ha_state = MagicMock()

    await switch.async_turn_on()
    coordinator.async_pulse.assert_awaited_once_with(0, 600, "HA-UI")

    coordinator.channel_configs[0].mode = ChannelMode.SWITCH
    await switch.async_turn_on()
    coordinator.async_write_coil.assert_awaited_once_with(0, True, "HA-UI")

    await switch.async_turn_off()  # always a hard off, even in pulse mode
    coordinator.async_write_coil.assert_awaited_with(0, False, "HA-UI")


def make_stats_coordinator():
    coordinator = make_coordinator_mock(("L",))
    coordinator.channel_stats = [{
        "ein_zaehler": 0, "aus_zaehler": 0, "schreibfehler": 0,
        "letzter_befehl": "", "letzter_impuls": "", "zustand": False,
        "letzter_wechsel": None, "einschaltdauer_s": 0.0, "ausschaltdauer_s": 100.0,
    }]
    coordinator.get_channel_stats = lambda ch: {
        **coordinator.channel_stats[ch], "ausschaltdauer_s": 140.0
    }
    return coordinator


def test_duration_sensor_freezes_and_throttles():
    coordinator = make_stats_coordinator()
    entry = MagicMock(entry_id="e1")
    with patch.object(sensor_mod.CoordinatorEntity, "__init__", patch_ce):
        sensor = sensor_mod.WaveshareChannelDurationSensor(coordinator, entry, 0, "aus")
    writes = []
    sensor.async_write_ha_state = lambda: writes.append(1)

    sensor._handle_coordinator_update()
    sensor._handle_coordinator_update()
    assert len(writes) == 1  # unchanged value: throttled to one per minute

    coordinator.channel_stats[0]["ausschaltdauer_s"] = 105.0  # real relay change
    sensor._handle_coordinator_update()
    assert len(writes) == 2
    assert sensor.native_value == 105.0
    assert sensor.extra_state_attributes == {"aktuell_s": 140.0}


def test_global_sensor_throttle_spares_error_counters():
    coordinator = make_stats_coordinator()
    entry = MagicMock(entry_id="e1")
    def build(key):
        with patch.object(sensor_mod.CoordinatorEntity, "__init__", patch_ce):
            return sensor_mod.WaveshareGlobalSensor(
                coordinator, entry,
                {"key": key, "name": key, "icon": "x", "unit": None, "cls": None},
            )
    churny = build("letzte_abfrage_ms")
    errors = build("abfragen_fehler")
    churn_writes, error_writes = [], []
    churny.async_write_ha_state = lambda: churn_writes.append(1)
    errors.async_write_ha_state = lambda: error_writes.append(1)

    churny._handle_coordinator_update()
    churny._handle_coordinator_update()
    errors._handle_coordinator_update()
    errors._handle_coordinator_update()
    assert len(churn_writes) == 1  # high-frequency value: throttled
    assert len(error_writes) == 2  # errors stay immediate


async def test_mode_select_persists_and_is_idempotent():
    coordinator = make_coordinator_mock(("Tor",))
    coordinator.channel_configs = [ChannelConfig(channel=0, name="Tor", pulse_duration_ms=700)]
    entry = MagicMock(entry_id="e1")
    entry.options = {}
    hass = MagicMock()
    hass.config_entries.async_update_entry.side_effect = (
        lambda ent, options=None, **kw: setattr(ent, "options", options or {})
    )
    with patch.object(ent.CoordinatorEntity, "__init__", patch_ce):
        select = select_mod.WaveshareChannelModeSelect(coordinator, entry, 0)
    select.hass = hass

    assert select.current_option == "Switch"
    assert select.options == ["Switch", "Pulse"]

    await select.async_select_option("Pulse")
    assert entry.options[CONF_CHANNEL_CONFIGS]["0"] == {
        "name": "Tor", "pulse_duration_ms": 700, "mode": "pulse",
    }
    await select.async_select_option("Pulse")  # no-op, no rewrite
    assert hass.config_entries.async_update_entry.call_count == 1
    assert select.current_option == "Pulse"


async def test_options_flow_two_steps():
    from custom_components.waveshare_relay import config_flow as cf

    entry = MagicMock(entry_id="e1")
    entry.options = {}
    coordinator = MagicMock()
    coordinator.channel_configs = [
        ChannelConfig(channel=0, name="Lampe"),
        ChannelConfig(channel=1, name="Relais 2", mode=ChannelMode.PULSE, pulse_duration_ms=700),
    ]
    hass = MagicMock()
    hass.data = {pkg.DOMAIN: {"e1": coordinator}}
    hass.config_entries.async_get_known_entry = lambda eid: entry if eid == "e1" else None

    handler = cf.WaveshareRelayConfigFlow.async_get_options_flow(entry)
    handler.handler = "e1"
    handler.hass = hass

    result = await handler.async_step_init(None)
    assert result["type"] == "form" and result["step_id"] == "init"

    result = await handler.async_step_init({"channel": "1"})
    assert result["type"] == "form" and result["step_id"] == "channel"
    assert result["description_placeholders"] == {"channel_number": "2"}

    result = await handler.async_step_channel(
        {"channel_name": "Garage", "betriebsart": "pulse", "impulsdauer_ms": 650}
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {
        "channel_configs": {"1": {"name": "Garage", "mode": "pulse", "pulse_duration_ms": 650}}
    }
