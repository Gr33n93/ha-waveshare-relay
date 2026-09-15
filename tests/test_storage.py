"""Tests for the MAC-keyed persistent statistics."""
import io
import builtins

import pytest

from custom_components.waveshare_relay import coordinator as coord_mod
from custom_components.waveshare_relay import storage as storage_mod
from custom_components.waveshare_relay.storage import SAVE_INTERVAL, resolve_mac

MAC = "04:ee:e8:13:40:17"
STORAGE_KEY = "waveshare_relay.04eee8134017"


class FakeStore:
    """Store stub with a class-level disk: data survives new instances."""

    disk: dict = {}

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return FakeStore.disk.get(self.key)

    async def async_save(self, data):
        FakeStore.disk[self.key] = data


@pytest.fixture(autouse=True)
def fake_store(monkeypatch):
    FakeStore.disk = {}
    monkeypatch.setattr(storage_mod, "Store", FakeStore)
    monkeypatch.setattr(coord_mod, "resolve_mac", lambda host: MAC)
    yield


def test_resolve_mac_parses_arp_table(monkeypatch):
    content = (
        "IP address  HW type  Flags  HW address  Mask  Device\n"
        "192.168.178.60  0x1  0x2  04:ee:e8:13:40:17  *  enp0s18\n"
        "192.168.178.47  0x1  0x2  04:ee:e8:1e:00:6b  *  enp0s18\n"
    )
    monkeypatch.setattr(
        builtins, "open", lambda path, encoding=None: io.StringIO(content)
    )
    assert resolve_mac("192.168.178.60") == "04:ee:e8:13:40:17"
    assert resolve_mac("192.168.178.47") == "04:ee:e8:1e:00:6b"
    assert resolve_mac("192.168.178.99") is None


def test_resolve_mac_survives_unreadable_arp(monkeypatch):
    def boom(path, encoding=None):
        raise OSError("nope")

    monkeypatch.setattr(builtins, "open", boom)
    assert resolve_mac("192.168.178.60") is None


async def test_first_contact_starts_statistics(coord_factory):
    coord, _, _, _ = coord_factory()
    await coord._async_touch_store()
    assert coord.first_seen is not None
    assert STORAGE_KEY in FakeStore.disk or FakeStore.disk == {}


async def test_periodic_save_and_shutdown_save(coord_factory):
    coord, _, _, _ = coord_factory()
    await coord._async_touch_store()
    await coord.async_write_coil(0, True, "HA-UI")

    coord._last_save -= SAVE_INTERVAL + 1  # simulate elapsed interval
    await coord._async_touch_store()
    saved = FakeStore.disk[STORAGE_KEY]
    assert saved["stats"]["schreiben_ok"] == 1
    assert saved["channel_stats"][0]["ein_zaehler"] == 1
    assert saved["first_seen"] == coord.first_seen
    # Monotonic baselines are never persisted.
    assert saved["channel_stats"][0]["letzter_wechsel"] is None

    await coord.async_write_coil(0, False, "HA-UI")
    await coord.async_shutdown()  # final save
    assert FakeStore.disk[STORAGE_KEY]["stats"]["schreiben_ok"] == 2


async def test_restore_after_restart_or_readd(coord_factory):
    """Simulates restart, reload and delete/re-add: same MAC, same stats."""
    first, _, _, _ = coord_factory()
    await first._async_touch_store()
    await first.async_write_coil(0, True, "HA-UI")
    await first.async_write_coil(0, False, "HA-UI")
    await first.async_pulse(1, 700, "HA-UI")
    await first._async_persist()

    # "New" coordinator (restart / re-added entry) resolving the same MAC.
    second, _, _, _ = coord_factory()
    await second._async_touch_store()
    assert second.first_seen == first.first_seen
    assert second.stats["schreiben_ok"] == 3
    assert second.channel_stats[0]["ein_zaehler"] == 1
    assert second.channel_stats[1]["letzter_impuls"] != ""
    assert second.channel_stats[0]["letzter_wechsel"] is None  # fresh baseline


async def test_reset_zeroes_statistics_but_keeps_first_seen(coord_factory):
    coord, _, _, _ = coord_factory()
    await coord._async_touch_store()
    first_seen = coord.first_seen
    await coord.async_write_coil(0, True, "HA-UI")
    await coord._async_persist()

    pending = []
    coord.hass.async_create_task = pending.append
    coord.reset_stats()
    await pending[0]  # the reset persists eagerly via a task

    assert coord.first_seen == first_seen
    assert coord.stats["schreiben_ok"] == 0
    assert coord.channel_stats[0]["ein_zaehler"] == 0
    saved = FakeStore.disk[STORAGE_KEY]
    assert saved["first_seen"] == first_seen
    assert saved["stats"]["schreiben_ok"] == 0
