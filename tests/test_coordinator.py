"""Tests for the coordinator: write paths, guards, statistics, config adoption."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

import custom_components.waveshare_relay as pkg
from custom_components.waveshare_relay import coordinator as coord_mod
from custom_components.waveshare_relay.models import ChannelConfig, ChannelMode
from conftest import FakeResult


async def test_partial_configs_are_padded(coord_factory):
    coord, _, _, _ = coord_factory(
        configs=[ChannelConfig(channel=0, name="A"), ChannelConfig(channel=1, name="B")]
    )
    assert coord.relay_names == ["A", "B", "Relais 3", "Relais 4"]


async def test_write_path(coord_factory):
    coord, write, _, timers = coord_factory()
    await coord.async_write_coil(0, True, "HA-UI")
    assert coord.relay_states[0] is True
    assert coord.channel_stats[0]["ein_zaehler"] == 1
    await coord.async_write_coil(0, False, "alle_aus")
    assert coord.channel_stats[0]["aus_zaehler"] == 1
    assert write.call_args.kwargs == {"address": 0, "value": False, "unit_id": 1}
    assert not timers  # plain writes never schedule a refresh


async def test_pulse_path(coord_factory):
    coord, _, pulse, timers = coord_factory()
    await coord.async_pulse(1, 700, "HA-UI")
    assert pulse.call_args.kwargs == {
        "address": 0x0201,
        "duration_ms": 700,
        "unit_id": 1,
    }
    # Optimistic on, pulse timestamp recorded, refresh after 700+300 ms.
    assert coord.relay_states[1] is True
    assert coord.channel_stats[1]["letzter_impuls"] != ""
    assert len(timers) == 1 and abs(timers[0][0] - 1.0) < 1e-9
    await timers[0][1](None)
    coord.async_request_refresh.assert_awaited_once()


async def test_duty_accumulation(coord_factory):
    coord, _, _, _ = coord_factory()
    clock = 1000.0
    with patch(
        "custom_components.waveshare_relay.coordinator.time.monotonic",
        side_effect=lambda: clock,
    ):
        coord._apply_relay_state(0, True, clock)
        clock += 10
        coord._apply_relay_state(0, False, clock)
        clock += 20
        coord._apply_relay_state(0, True, clock)
        clock += 5
        stats = coord.channel_stats[0]
        assert stats["einschaltdauer_s"] == 10.0
        assert stats["ausschaltdauer_s"] == 20.0
        # Live view adds the currently elapsed time.
        assert coord.get_channel_stats(0)["einschaltdauer_s"] == 15.0


async def test_manual_commands_blocked_during_test(coord_factory):
    coord, _, _, _ = coord_factory()
    coord.test_running = True
    with pytest.raises(HomeAssistantError):
        await coord.async_write_coil(0, True, "HA-UI")
    with pytest.raises(HomeAssistantError):
        await coord.async_pulse(1, 500, "HA-UI")
    # All-off stays available as the safety stop.
    await coord.async_write_coil(0, False, "alle_aus")


async def test_function_test_race_and_stuck_flag(coord_factory):
    coord, _, _, _ = coord_factory()
    await coord.async_start_test(1, 0.1, True)
    assert coord.test_running is True  # set synchronously
    first_task = coord._test_task
    await coord.async_start_test(1, 0.1, True)
    assert coord._test_task is first_task  # no second test
    await coord.async_stop_test()
    assert coord.test_running is False  # reset even if the task never ran


async def test_modbus_error_counted_and_translated(coord_factory):
    coord, _, _, _ = coord_factory()
    coord_mod.write_coil_compat = AsyncMock(return_value=FakeResult(err=True))
    with pytest.raises(HomeAssistantError) as exc_info:
        await coord.async_write_coil(3, True)
    assert exc_info.value.translation_domain == coord_mod.DOMAIN
    assert exc_info.value.translation_key == "write_failed"
    assert exc_info.value.translation_placeholders == {"channel": "4"}
    for language in ("en", "de"):
        path = Path(__file__).parents[1] / (
            f"custom_components/waveshare_relay/translations/{language}.json"
        )
        message = json.loads(path.read_text())["exceptions"]["write_failed"]["message"]
        assert "4" in message.format(**exc_info.value.translation_placeholders)
    assert coord.stats["schreiben_fehler"] == 1
    assert coord.channel_stats[3]["schreibfehler"] == 1


async def test_all_off_reports_failed_channels_and_logs_details(coord_factory, caplog):
    coord, write, _, _ = coord_factory()
    write.side_effect = [
        FakeResult(), FakeResult(err=True), FakeResult(err=True), FakeResult()
    ]

    with pytest.raises(HomeAssistantError) as exc_info:
        await coord.async_all_off()

    error = exc_info.value
    assert write.await_count == 4
    assert error.translation_key == "all_off_incomplete"
    assert error.translation_placeholders == {"channels": "2, 3"}
    assert "channel 2 error" in caplog.text
    assert "channel 3 error" in caplog.text
    for language, label in (("en", "Failed channels: 2, 3"), ("de", "Fehlgeschlagene Kanäle: 2, 3")):
        path = Path(__file__).parents[1] / f"custom_components/waveshare_relay/translations/{language}.json"
        message = json.loads(path.read_text())["exceptions"][error.translation_key]["message"]
        assert label in message.format(**error.translation_placeholders)


async def test_first_poll_connection_failure_is_translated_and_records_details(
    coord_factory,
):
    coord, _, _, _ = coord_factory()
    client = MagicMock()
    client.connected = False
    client.connect = AsyncMock(return_value=False)
    with patch.object(coord_mod, "AsyncModbusTcpClient", return_value=client):
        with pytest.raises(coord_mod.UpdateFailed) as exc_info:
            await coord._async_update_data()

    assert exc_info.value.translation_domain == coord_mod.DOMAIN
    assert exc_info.value.translation_key == "connection_failed"
    assert exc_info.value.translation_placeholders == {
        "host": "board",
        "port": "502",
    }
    for language, label in (
        ("en", "board:502"),
        ("de", "board:502"),
    ):
        path = Path(__file__).parents[1] / (
            f"custom_components/waveshare_relay/translations/{language}.json"
        )
        message = json.loads(path.read_text())["exceptions"][
            exc_info.value.translation_key
        ]["message"]
        assert label in message.format(**exc_info.value.translation_placeholders)
    assert coord.stats["verbunden"] is False
    assert coord.stats["abfragen_fehler"] == 1
    assert coord.stats["letzte_fehlermeldung"] == (
        "Modbus connection failed: Connection to board:502 failed"
    )
    client.close.assert_called_once()


async def test_write_connection_failure_is_translated(coord_factory):
    coord, _, _, _ = coord_factory()
    coord._ensure_connected = AsyncMock(
        side_effect=ConnectionError("connection refused")
    )

    with pytest.raises(HomeAssistantError) as exc_info:
        await coord.async_write_coil(0, True)

    error = exc_info.value
    assert error.translation_key == "connection_failed"
    assert error.translation_placeholders == {"host": "board", "port": "502"}
    assert "connection refused" not in str(error)


async def test_setup_retry_has_translated_reason_and_preserves_cause():
    hass = MagicMock()
    entry = MagicMock(entry_id="e1")
    entry.data = {"host": "board", "port": 502, "unit_id": 1}
    entry.options = {}
    coordinator = MagicMock(host="board", port=502)
    original = ConfigEntryNotReady("Polling failed: connection refused")
    coordinator.async_config_entry_first_refresh = AsyncMock(side_effect=original)

    with (
        patch.object(pkg.dr, "async_get") as registry,
        patch.object(pkg, "WaveshareRelayCoordinator", return_value=coordinator),
        pytest.raises(ConfigEntryNotReady) as exc_info,
    ):
        registry.return_value.async_get_device_by_identifier.return_value = None
        await pkg.async_setup_entry(hass, entry)

    error = exc_info.value
    assert error.__cause__ is original
    assert str(error) == "Polling failed: connection refused"
    assert error.translation_domain == pkg.DOMAIN
    assert error.translation_key == "setup_poll_failed"
    assert error.translation_placeholders == {"host": "board", "port": "502"}
    for language in ("en", "de"):
        path = Path(__file__).parents[1] / f"custom_components/waveshare_relay/translations/{language}.json"
        message = json.loads(path.read_text())["exceptions"][error.translation_key]["message"]
        assert "board:502" in message.format(**error.translation_placeholders)
    hass.config_entries.async_forward_entry_setups.assert_not_called()


async def test_mode_switch_preserves_statistics(coord_factory):
    coord, _, _, _ = coord_factory()
    await coord.async_write_coil(0, True, "HA-UI")
    stats_snapshot = dict(coord.stats)
    channel_snapshot = [dict(s) for s in coord.channel_stats]

    coord.apply_channel_configs(
        [ChannelConfig(channel=0, name="Garage", mode=ChannelMode.PULSE)]
    )
    assert coord.channel_configs[0].mode is ChannelMode.PULSE
    assert coord.stats == stats_snapshot
    assert coord.channel_stats == channel_snapshot
    assert coord.relay_names == ["Garage", "Relais 2", "Relais 3", "Relais 4"]


async def test_update_listener_applies_in_place(coord_factory):
    coord, _, _, _ = coord_factory()
    hass = MagicMock()
    hass.data = {pkg.DOMAIN: {"e1": coord}}
    entry = MagicMock(entry_id="e1")
    entry.options = {
        "channel_configs": {
            "0": {"name": "Tor", "mode": "pulse", "pulse_duration_ms": 900}
        }
    }
    entry.data = {"relay_count": 4}

    await pkg._async_update_listener(hass, entry)
    config = coord.channel_configs[0]
    assert (config.name, config.mode, config.pulse_duration_ms) == (
        "Tor",
        ChannelMode.PULSE,
        900,
    )
    hass.config_entries.async_reload.assert_not_called()
