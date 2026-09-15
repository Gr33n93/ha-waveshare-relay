"""Shared fixtures and fakes for the waveshare_relay test suite."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from custom_components.waveshare_relay import coordinator as coord_mod  # noqa: E402


class FakeResult:
    """Minimal Modbus result stub."""

    def __init__(self, err: bool = False) -> None:
        self._err = err

    def isError(self) -> bool:
        return self._err


class FakeClient:
    """Always-connected Modbus client stub."""

    connected = True

    async def connect(self) -> bool:
        return True

    def close(self) -> None:
        pass


def patch_ce(self, coordinator) -> None:
    """Replacement for CoordinatorEntity.__init__ in entity tests."""
    self.coordinator = coordinator


@pytest.fixture
def coord_factory():
    """Build coordinators with mocked Modbus I/O.

    Returns (coordinator, write_mock, pulse_mock, timers) where timers
    collects the (delay, callback) pairs passed to async_call_later.
    """

    def factory(relay_count: int = 4, configs=None):
        hass = MagicMock()
        hass.async_create_task = asyncio.get_running_loop().create_task
        coord_mod.AsyncModbusTcpClient = MagicMock(return_value=FakeClient())
        pulse = AsyncMock(return_value=FakeResult())
        write = AsyncMock(return_value=FakeResult())
        coord_mod.write_pulse_compat = pulse
        coord_mod.write_coil_compat = write
        timers: list = []
        coord_mod.async_call_later = (
            lambda h, d, a: (timers.append((d, a)), MagicMock())[-1]
        )
        with patch.object(
            coord_mod.DataUpdateCoordinator, "__init__", lambda s, *a, **k: None
        ):
            coord = coord_mod.WaveshareRelayCoordinator(
                hass, "board", 502, 1, relay_count=relay_count, channel_configs=configs
            )
        coord.hass = hass
        coord.async_set_updated_data = MagicMock()
        coord.async_request_refresh = AsyncMock()
        return coord, write, pulse, timers

    return factory
