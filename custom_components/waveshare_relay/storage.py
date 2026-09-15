"""Persistent statistics storage keyed by the board MAC address.

Statistics survive restarts, reloads and even deleting and re-adding the
board, because the storage key is derived from the board MAC (resolved
from the host ARP table) instead of the config entry. The first-connection
date is a board fact and survives statistics resets.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_INTERVAL = 300  # persist at most every 5 minutes (plus on shutdown)


def resolve_mac(host: str) -> str | None:
    """Resolve the MAC address of host from the kernel ARP table.

    The HA core container runs with host networking on HA OS, so
    /proc/net/arp reflects the host table. Because the coordinator
    polls the board constantly, the entry is always fresh.
    """
    try:
        with open("/proc/net/arp", encoding="utf-8") as arp_file:
            for line in arp_file:
                fields = line.split()
                if len(fields) >= 4 and fields[0] == host:
                    return fields[3].lower()
    except OSError:
        _LOGGER.debug("ARP table not readable, falling back to IP key")
    return None


class WaveshareStatsStore:
    """Thin wrapper around HA's Store for one board's statistics."""

    def __init__(self, hass: HomeAssistant, board_key: str) -> None:
        self._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{board_key}")

    async def async_load(self) -> dict[str, Any] | None:
        """Load the persisted snapshot, if any."""
        return await self._store.async_load()

    async def async_save(
        self, first_seen: str, stats: dict, channel_stats: list[dict]
    ) -> None:
        """Persist a snapshot; monotonic baselines are not stored."""
        await self._store.async_save(
            {
                "first_seen": first_seen,
                "stats": stats,
                "channel_stats": [
                    {**cs, "letzter_wechsel": None} for cs in channel_stats
                ],
            }
        )
