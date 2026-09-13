"""Datenmodelle: Kanalprofile für Dauerbetrieb und Impuls.

Bewusst ohne Home-Assistant-Importe, damit die Struktur lokal testbar bleibt.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .const import (
    CONF_CHANNEL_CONFIGS,
    DEFAULT_PULSE_DURATION_MS,
    MAX_PULSE_DURATION_MS,
    MIN_PULSE_DURATION_MS,
    MODE_PULSE,
)


class ChannelMode(StrEnum):
    """Betriebsart eines Relaiskanals."""

    SWITCH = "switch"  # Dauerbetrieb
    PULSE = "pulse"  # Impuls


@dataclass
class ChannelConfig:
    """Profil eines einzelnen Relaiskanals."""

    channel: int
    name: str
    mode: ChannelMode = ChannelMode.SWITCH
    pulse_duration_ms: int = DEFAULT_PULSE_DURATION_MS


def default_channel_configs(relay_count: int) -> list[ChannelConfig]:
    """Standardprofile erzeugen: alle Kanäle im Dauerbetrieb."""
    return [
        ChannelConfig(channel=i, name=f"Relais {i + 1}") for i in range(relay_count)
    ]


def channel_configs_from_entry(
    entry_options: dict, relay_count: int
) -> list[ChannelConfig]:
    """Kanalprofile aus entry.options lesen.

    Fehlende oder ungültige Einträge fallen auf Dauerbetrieb mit
    Standardnamen zurück – ein Update ändert dadurch nichts an
    bestehenden Installationen.
    """
    raw: dict = entry_options.get(CONF_CHANNEL_CONFIGS) or {}
    defaults = default_channel_configs(relay_count)

    configs: list[ChannelConfig] = []
    for i in range(relay_count):
        item = raw.get(str(i)) or {}
        try:
            duration = int(item.get("pulse_duration_ms", DEFAULT_PULSE_DURATION_MS))
        except (TypeError, ValueError):
            duration = DEFAULT_PULSE_DURATION_MS
        duration = max(MIN_PULSE_DURATION_MS, min(MAX_PULSE_DURATION_MS, duration))

        mode = ChannelMode.PULSE if item.get("mode") == MODE_PULSE else ChannelMode.SWITCH
        name = str(item.get("name") or "").strip() or defaults[i].name
        configs.append(
            ChannelConfig(
                channel=i,
                name=name,
                mode=mode,
                pulse_duration_ms=duration,
            )
        )
    return configs
