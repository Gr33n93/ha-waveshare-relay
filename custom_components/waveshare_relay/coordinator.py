"""DataUpdateCoordinator für Waveshare PoE Relay – Modbus TCP."""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Any

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_POLL_INTERVAL, DEFAULT_RELAY_COUNT
from .modbus_compat import read_coils_compat, write_coil_compat

_LOGGER = logging.getLogger(__name__)


class WaveshareRelayCoordinator(DataUpdateCoordinator):
    """Koordinator: Modbus-Polling, Statistik, Dauer-Tracking, Funktionstest."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        unit_id: int,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        relay_count: int = DEFAULT_RELAY_COUNT,
        relay_names: list[str] | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self.host = host
        self.port = port
        self.unit_id = unit_id
        self.relay_count = relay_count
        self.relay_names = relay_names or [
            f"Relais {i}" for i in range(1, self.relay_count + 1)
        ]

        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()

        self.relay_states: list[bool] = [False] * self.relay_count

        self.stats: dict[str, Any] = {
            "abfragen_gesamt": 0,
            "abfragen_ok": 0,
            "abfragen_fehler": 0,
            "letzte_abfrage_ms": 0.0,
            "schreibvorgaenge_gesamt": 0,
            "schreiben_ok": 0,
            "schreiben_fehler": 0,
            "letzte_fehlermeldung": "",
            "letzter_fehler_zeit": "",
            "letzter_erfolg_zeit": "",
            "verbunden": False,
        }

        self.channel_stats: list[dict[str, Any]] = []
        for _ in range(self.relay_count):
            self.channel_stats.append({
                "ein_zaehler": 0,
                "aus_zaehler": 0,
                "schreibfehler": 0,
                "letzter_befehl": "",
                "zustand": False,
                "letzter_wechsel": None,
                "einschaltdauer_s": 0.0,
                "ausschaltdauer_s": 0.0,
            })

        self.test_running = False
        self.test_stop = False
        self.test_current_channel = 0
        self._test_task: asyncio.Task | None = None

    # ─────────────── Modbus Connection ───────────────

    async def _ensure_connected(self) -> AsyncModbusTcpClient:
        if self._client and self._client.connected:
            return self._client
        try:
            self._client = AsyncModbusTcpClient(
                host=self.host, port=self.port, timeout=3, retries=1,
            )
            connected = await self._client.connect()
            if not connected:
                raise ConnectionError(
                    f"Verbindung zu {self.host}:{self.port} fehlgeschlagen"
                )
            self.stats["verbunden"] = True
            _LOGGER.debug("Modbus-Verbindung hergestellt: %s:%s", self.host, self.port)
            return self._client
        except Exception as err:
            self.stats["verbunden"] = False
            raise ConnectionError(
                f"Modbus-Verbindung fehlgeschlagen: {err}"
            ) from err

    async def async_shutdown(self) -> None:
        await self.async_stop_test()
        if self._client:
            self._client.close()
            self._client = None

    def _apply_relay_state(
        self, channel: int, new_state: bool, now_mono: float | None = None
    ) -> None:
        """Lokalen Zustand übernehmen und Dauerzähler bei Wechsel fortschreiben."""
        now_mono = now_mono or time.monotonic()
        old_state = self.relay_states[channel]
        cs = self.channel_stats[channel]
        last_change = cs["letzter_wechsel"]

        if new_state != old_state and last_change is not None:
            delta = now_mono - last_change
            if old_state:
                cs["einschaltdauer_s"] = round(cs["einschaltdauer_s"] + delta, 2)
            else:
                cs["ausschaltdauer_s"] = round(cs["ausschaltdauer_s"] + delta, 2)

        if new_state != old_state or last_change is None:
            cs["letzter_wechsel"] = now_mono

        cs["zustand"] = new_state
        self.relay_states[channel] = new_state

    def get_channel_stats(self, channel: int) -> dict[str, Any]:
        """Kanalstatistik mit live fortgeschriebener aktueller Dauer zurückgeben."""
        cs = dict(self.channel_stats[channel])
        last_change = cs["letzter_wechsel"]
        if last_change is not None:
            elapsed = time.monotonic() - last_change
            if cs["zustand"]:
                cs["einschaltdauer_s"] = round(cs["einschaltdauer_s"] + elapsed, 2)
            else:
                cs["ausschaltdauer_s"] = round(cs["ausschaltdauer_s"] + elapsed, 2)
        return cs

    # ─────────────── Modbus Lesen (FC01) ───────────────

    async def _async_update_data(self) -> dict[str, Any]:
        t0 = time.monotonic()
        self.stats["abfragen_gesamt"] += 1
        try:
            async with self._lock:
                client = await self._ensure_connected()
                result = await read_coils_compat(
                    client, address=0, count=self.relay_count, unit_id=self.unit_id
                )
            if result.isError():
                raise UpdateFailed(f"FC01-Fehler: {result}")

            now_mono = time.monotonic()
            elapsed_ms = round((now_mono - t0) * 1000, 1)
            self.stats["abfragen_ok"] += 1
            self.stats["letzte_abfrage_ms"] = elapsed_ms
            self.stats["letzter_erfolg_zeit"] = _iso_now()
            self.stats["verbunden"] = True

            for i in range(self.relay_count):
                new_state = bool(result.bits[i])
                self._apply_relay_state(i, new_state, now_mono)

            return {"relay_states": self.relay_states, "stats": self.stats}

        except Exception as err:
            self.stats["abfragen_fehler"] += 1
            self.stats["letzte_abfrage_ms"] = round(
                (time.monotonic() - t0) * 1000, 1
            )
            self.stats["letzte_fehlermeldung"] = str(err)
            self.stats["letzter_fehler_zeit"] = _iso_now()
            self.stats["verbunden"] = False
            if self._client:
                self._client.close()
                self._client = None
            raise UpdateFailed(f"Abfrage fehlgeschlagen: {err}") from err

    # ─────────────── Modbus Schreiben (FC05) ───────────────

    async def async_write_coil(
        self, channel: int, value: bool, source: str = "manuell"
    ) -> None:
        self.stats["schreibvorgaenge_gesamt"] += 1
        cs = self.channel_stats[channel]
        try:
            async with self._lock:
                client = await self._ensure_connected()
                result = await write_coil_compat(
                    client, address=channel, value=value, unit_id=self.unit_id
                )
            if result.isError():
                raise ModbusException(
                    f"FC05-Fehler Kanal {channel + 1}: {result}"
                )

            self.stats["schreiben_ok"] += 1
            self.stats["letzter_erfolg_zeit"] = _iso_now()
            if value:
                cs["ein_zaehler"] += 1
            else:
                cs["aus_zaehler"] += 1
            cs["letzter_befehl"] = f"{_iso_now()} ({source})"

            self._apply_relay_state(channel, value)
            self.async_set_updated_data(
                {"relay_states": self.relay_states, "stats": self.stats}
            )
        except Exception as err:
            self.stats["schreiben_fehler"] += 1
            cs["schreibfehler"] += 1
            self.stats["letzte_fehlermeldung"] = str(err)
            self.stats["letzter_fehler_zeit"] = _iso_now()
            _LOGGER.error("Schreiben Kanal %d fehlgeschlagen: %s", channel + 1, err)
            raise

    async def async_all_off(self) -> None:
        errors: list[str] = []
        for ch in range(self.relay_count):
            try:
                await self.async_write_coil(ch, False, "alle_aus")
            except Exception as err:
                _LOGGER.warning("Alle-Aus: Kanal %d Fehler: %s", ch + 1, err)
                errors.append(f"Kanal {ch + 1}: {err}")
        if errors:
            raise HomeAssistantError(
                "Alle-Aus unvollständig: " + "; ".join(errors)
            )

    # ─────────────── Funktionstest ───────────────

    async def async_start_test(
        self,
        laufzeit_s: float = 5.0,
        pause_s: float = 0.25,
        einmalig: bool = True,
    ) -> None:
        if self.test_running:
            _LOGGER.warning("Funktionstest läuft bereits")
            return
        self.test_stop = False
        self._test_task = self.hass.async_create_task(
            self._run_test(laufzeit_s, pause_s, einmalig)
        )

    async def _run_test(
        self, laufzeit_s: float, pause_s: float, einmalig: bool
    ) -> None:
        self.test_running = True
        self.test_current_channel = 0
        _LOGGER.info(
            "Funktionstest gestartet: Laufzeit=%.1fs, Pause=%.2fs, Einmalig=%s",
            laufzeit_s, pause_s, einmalig,
        )
        try:
            await self.async_all_off()
            while True:
                for ch in range(self.relay_count):
                    if self.test_stop:
                        return
                    self.test_current_channel = ch + 1
                    self.async_set_updated_data(
                        {"relay_states": self.relay_states, "stats": self.stats}
                    )
                    await self.async_write_coil(ch, True, "Funktionstest")
                    await asyncio.sleep(laufzeit_s)
                    if self.test_stop:
                        return
                    await self.async_write_coil(ch, False, "Funktionstest")
                    if pause_s > 0:
                        await asyncio.sleep(pause_s)
                if einmalig:
                    break
        except asyncio.CancelledError:
            _LOGGER.info("Funktionstest abgebrochen")
        except Exception as err:
            _LOGGER.error("Funktionstest-Fehler: %s", err)
        finally:
            try:
                await self.async_all_off()
            except Exception:
                pass
            self.test_running = False
            self.test_current_channel = 0
            self.async_set_updated_data(
                {"relay_states": self.relay_states, "stats": self.stats}
            )
            _LOGGER.info("Funktionstest beendet")

    async def async_stop_test(self) -> None:
        self.test_stop = True
        task = self._test_task
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self._test_task = None

    # ─────────────── Statistik zurücksetzen ───────────────

    def reset_stats(self) -> None:
        connected = self.stats.get("verbunden", False)
        for key in self.stats:
            if isinstance(self.stats[key], bool):
                self.stats[key] = False
            elif isinstance(self.stats[key], (int, float)):
                self.stats[key] = 0
            elif isinstance(self.stats[key], str):
                self.stats[key] = ""
        self.stats["verbunden"] = connected
        now_mono = time.monotonic()
        for index, cs in enumerate(self.channel_stats):
            cs["ein_zaehler"] = 0
            cs["aus_zaehler"] = 0
            cs["schreibfehler"] = 0
            cs["letzter_befehl"] = ""
            cs["zustand"] = self.relay_states[index]
            cs["einschaltdauer_s"] = 0.0
            cs["ausschaltdauer_s"] = 0.0
            cs["letzter_wechsel"] = now_mono
        self.async_set_updated_data(
            {"relay_states": self.relay_states, "stats": self.stats}
        )
        _LOGGER.info("Statistik zurückgesetzt")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
