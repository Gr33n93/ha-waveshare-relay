"""Tests for channel profile parsing and defaults."""
import pytest

from custom_components.waveshare_relay.models import (
    ChannelMode,
    channel_configs_from_entry,
    default_channel_configs,
)


def test_defaults_are_all_switch():
    configs = default_channel_configs(8)
    assert len(configs) == 8
    assert all(c.mode is ChannelMode.SWITCH for c in configs)
    assert configs[0].name == "Relais 1"
    assert configs[7].name == "Relais 8"
    assert all(c.pulse_duration_ms == 500 for c in configs)


def test_empty_options_behave_like_defaults():
    """Existing installations without options keep their behaviour."""
    configs = channel_configs_from_entry({}, 16)
    assert len(configs) == 16
    assert all(c.mode is ChannelMode.SWITCH for c in configs)
    assert configs[15].name == "Relais 16"


def test_parse_full_channel_config():
    options = {
        "channel_configs": {
            "2": {"name": "Garagentor", "mode": "pulse", "pulse_duration_ms": 700}
        }
    }
    configs = channel_configs_from_entry(options, 8)
    assert configs[2].name == "Garagentor"
    assert configs[2].mode is ChannelMode.PULSE
    assert configs[2].pulse_duration_ms == 700
    # Unconfigured neighbours stay on defaults
    assert configs[1].mode is ChannelMode.SWITCH
    assert configs[1].name == "Relais 2"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("50", 100), (99999, 10000), ("abc", 500), (None, 500), (700, 700)],
)
def test_pulse_duration_clamping(raw, expected):
    options = {"channel_configs": {"0": {"mode": "pulse", "pulse_duration_ms": raw}}}
    assert channel_configs_from_entry(options, 1)[0].pulse_duration_ms == expected


@pytest.mark.parametrize(
    ("item", "expect_mode", "expect_name"),
    [
        ({"mode": "kaputt", "name": "Licht"}, ChannelMode.SWITCH, "Licht"),
        ({"mode": "pulse", "name": "   "}, ChannelMode.PULSE, "Relais 1"),
        ({}, ChannelMode.SWITCH, "Relais 1"),
    ],
)
def test_garbage_entries_fall_back(item, expect_mode, expect_name):
    options = {"channel_configs": {"0": item}}
    config = channel_configs_from_entry(options, 1)[0]
    assert config.mode is expect_mode
    assert config.name == expect_name
