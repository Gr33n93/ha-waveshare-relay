"""Data update coordinator for the Waveshare PoE relay (Modbus TCP)."""
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
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_POLL_INTERVAL, DEFAULT_RELAY_COUNT, PULSE_ADDR_ON
from .modbus_compat import read_coils_compat, write_coil_compat, write_pulse_compat
from .models import ChannelConfig, default_channel_configs
from .storage import SAVE_INTERVAL, WaveshareStatsStore, resolve_mac

_LOGGER = logging.getLogger(__name__)


def _fresh_stats() -> dict[str, Any]:
    """Board statistics template - single source for init and reset."""
    return {
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


def _fresh_channel_stats() -> dict[str, Any]:
    """Channel statistics template - single source for init and reset."""
    return {
        "ein_zaehler": 0,
        "aus_zaehler": 0,
        "schreibfehler": 0,
        "letzter_befehl": "",
        "letzter_impuls": "",
        "zustand": False,
        "letzter_wechsel": None,
        "einschaltdauer_s": 0.0,
        "ausschaltdauer_s": 0.0,
    }


class WaveshareRelayCoordinator(DataUpdateCoordinator):
    """Coordinator: Modbus polling, statistics, duty tracking, function test."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        unit_id: int,
        poll_interval: int = DEFAULT_POLL_INTERVAL,
        relay_count: int = DEFAULT_RELAY_COUNT,
        channel_configs: list[ChannelConfig] | None = None,
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
        # Channel profiles; apply_channel_configs pads missing entries and
        # wires relay_names - also at runtime after option changes.
        self.channel_configs: list[ChannelConfig] = []
        self.relay_names: list[str] = []
        self.apply_channel_configs(
            channel_configs or default_channel_configs(relay_count)
        )

        self._client: AsyncModbusTcpClient | None = None
        self._lock = asyncio.Lock()
        self._pulse_timers: dict[int, Any] = {}

        self.relay_states: list[bool] = [False] * self.relay_count
        self.stats = _fresh_stats()
        self.channel_stats = [
            _fresh_channel_stats() for _ in range(self.relay_count)
        ]

        self.test_running = False
        self.test_stop = False
        self.test_current_channel = 0
        self._test_task: asyncio.Task | None = None

        # Persistent statistics (keyed by board MAC once resolved)
        self.first_seen: str | None = None
        self._stats_store: WaveshareStatsStore | None = None
        self._last_save = 0.0

    def apply_channel_configs(self, configs: list[ChannelConfig]) -> None:
        """Adopt channel profiles - also at runtime, without a reload.

        Statistics and connections are fully preserved; missing channels
        fall back to continuous mode with the default name.
        """
        configs = list(configs)
        if len(configs) < self.relay_count:
            configs.extend(
                default_channel_configs(self.relay_count)[len(configs):]
            )
        self.channel_configs = configs
        self.relay_names = [c.name for c in configs]

    # ─────────────── Persistent statistics ───────────────

    async def _async_touch_store(self) -> None:
        """Restore statistics on first contact, then persist periodically.

        The storage key is the board MAC, so statistics survive restarts,
        reloads and deleting/re-adding the board.
        """
        now = time.monotonic()
        if self._stats_store is None:
            mac = resolve_mac(self.host)
            # Colons would end up in the storage file name; strip them.
            board_key = mac.replace(":", "") if mac else f"ip-{self.host}"
            self._stats_store = WaveshareStatsStore(self.hass, board_key)
            data = await self._stats_store.async_load()
            if data:
                self._merge_persisted(data)
            else:
                self.first_seen = _iso_now()
                _LOGGER.info("First contact with board %s, statistics start", self.host)
            self._last_save = now
            await self._async_persist()  # snapshot immediately
            return
        if now - self._last_save >= SAVE_INTERVAL:
            self._last_save = now
            await self._async_persist()

    def _merge_persisted(self, data: dict) -> None:
        """Adopt a persisted snapshot; monotonic baselines restart fresh."""
        self.first_seen = data.get("first_seen")
        for key, value in (data.get("stats") or {}).items():
            if key in self.stats:
                self.stats[key] = value
        self.stats["verbunden"] = True  # we just polled successfully
        stored_channels = data.get("channel_stats") or []
        for index, stored in enumerate(stored_channels[: self.relay_count]):
            cs = self.channel_stats[index]
            for key in (
                "ein_zaehler", "aus_zaehler", "schreibfehler",
                "einschaltdauer_s", "ausschaltdauer_s",
                "letzter_befehl", "letzter_impuls",
            ):
                if key in stored:
                    cs[key] = stored[key]
            cs["zustand"] = False  # corrected by the poll in flight
            cs["letzter_wechsel"] = None  # fresh monotonic baseline
        _LOGGER.info(
            "Statistics restored for board %s (first seen %s)",
            self.host, self.first_seen,
        )

    async def _async_persist(self) -> None:
        """Write the current snapshot to disk."""
        if self._stats_store is None or self.first_seen is None:
            return
        await self._stats_store.async_save(
            self.first_seen, self.stats, self.channel_stats
        )

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
            _LOGGER.debug("Modbus connection established: %s:%s", self.host, self.port)
            return self._client
        except Exception as err:
            self.stats["verbunden"] = False
            raise ConnectionError(
                f"Modbus-Verbindung fehlgeschlagen: {err}"
            ) from err

    async def async_shutdown(self) -> None:
        await self.async_stop_test()
        await self._async_persist()
        for cancel in self._pulse_timers.values():
            cancel()
        self._pulse_timers.clear()
        if self._client:
            self._client.close()
            self._client = None

    def _apply_relay_state(
        self, channel: int, new_state: bool, now_mono: float | None = None
    ) -> None:
        """Adopt the local state and advance duration counters on change."""
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
        """Return channel stats with the current duration added live."""
        cs = dict(self.channel_stats[channel])
        last_change = cs["letzter_wechsel"]
        if last_change is not None:
            elapsed = time.monotonic() - last_change
            if cs["zustand"]:
                cs["einschaltdauer_s"] = round(cs["einschaltdauer_s"] + elapsed, 2)
            else:
                cs["ausschaltdauer_s"] = round(cs["ausschaltdauer_s"] + elapsed, 2)
        return cs

    # ─────────────── Modbus read (FC01) ───────────────

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

            await self._async_touch_store()

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

    # ─────────────── Modbus write (FC05) ───────────────

    def _ensure_write_allowed(self, source: str) -> None:
        """Reject manual commands while a function test is running.

        Only the test itself and all-off (safety stop) are allowed, so
        manual switching cannot interleave with the test sequence.
        """
        if self.test_running and source not in ("Funktionstest", "alle_aus"):
            raise HomeAssistantError(
                "Funktionstest läuft – manuelle Schaltbefehle werden solange "
                "abgelehnt (Alle-Aus bleibt möglich)."
            )

    async def _async_write(
        self,
        channel: int,
        source: str,
        *,
        value: bool = False,
        pulse_duration_ms: int = 0,
    ) -> None:
        """Unified write path: FC05 write or native pulse.

        Centralizes lock, connection, statistics and error handling;
        async_write_coil and async_pulse are the public facades.
        """
        pulse = pulse_duration_ms > 0
        self._ensure_write_allowed(source)
        self.stats["schreibvorgaenge_gesamt"] += 1
        cs = self.channel_stats[channel]
        try:
            async with self._lock:
                client = await self._ensure_connected()
                if pulse:
                    result = await write_pulse_compat(
                        client,
                        address=PULSE_ADDR_ON + channel,
                        duration_ms=pulse_duration_ms,
                        unit_id=self.unit_id,
                    )
                else:
                    result = await write_coil_compat(
                        client, address=channel, value=value, unit_id=self.unit_id
                    )
            if result.isError():
                raise ModbusException(
                    f"{'Impuls' if pulse else 'FC05'}-Fehler Kanal {channel + 1}: {result}"
                )

            self.stats["schreiben_ok"] += 1
            self.stats["letzter_erfolg_zeit"] = _iso_now()
            if pulse or value:
                cs["ein_zaehler"] += 1
            else:
                cs["aus_zaehler"] += 1
            cs["letzter_befehl"] = f"{_iso_now()} ({source})"
            if pulse:
                cs["letzter_impuls"] = _iso_now()

            if pulse:
                # Optimistically switch on; after the pulse window the
                # board has already switched itself off again and is
                # read back through the scheduled refresh.
                self._apply_relay_state(channel, True)
            else:
                self._apply_relay_state(channel, value)
            self.async_set_updated_data(
                {"relay_states": self.relay_states, "stats": self.stats}
            )
            if pulse:
                self._schedule_pulse_refresh(channel, pulse_duration_ms)
        except Exception as err:
            self.stats["schreiben_fehler"] += 1
            cs["schreibfehler"] += 1
            self.stats["letzte_fehlermeldung"] = str(err)
            self.stats["letzter_fehler_zeit"] = _iso_now()
            _LOGGER.error(
                "%s channel %d failed: %s",
                "Pulse" if pulse else "Write", channel + 1, err,
            )
            raise

    async def async_write_coil(
        self, channel: int, value: bool, source: str = "manuell"
    ) -> None:
        """Switch a relay permanently on or off."""
        await self._async_write(channel, source, value=value)

    async def async_pulse(
        self, channel: int, duration_ms: int, source: str = "HA-UI"
    ) -> None:
        """Trigger a native Waveshare pulse; the board switches back off."""
        await self._async_write(channel, source, pulse_duration_ms=duration_ms)

    def _schedule_pulse_refresh(self, channel: int, duration_ms: int) -> None:
        """Read the board state again after the pulse window."""
        old = self._pulse_timers.pop(channel, None)
        if old is not None:
            old()

        async def _refresh(now: Any) -> None:
            self._pulse_timers.pop(channel, None)
            await self.async_request_refresh()

        self._pulse_timers[channel] = async_call_later(
            self.hass, (duration_ms + 300) / 1000, _refresh
        )

    async def async_all_off(self) -> None:
        errors: list[str] = []
        for ch in range(self.relay_count):
            try:
                await self.async_write_coil(ch, False, "alle_aus")
            except Exception as err:
                _LOGGER.warning("All-off: channel %d error: %s", ch + 1, err)
                errors.append(f"Kanal {ch + 1}: {err}")
        if errors:
            raise HomeAssistantError(
                "Alle-Aus unvollständig: " + "; ".join(errors)
            )

    # ─────────────── Function test ───────────────

    async def async_start_test(
        self,
        laufzeit_s: float = 5.0,
        pause_s: float = 0.25,
        einmalig: bool = True,
    ) -> None:
        if self.test_running:
            _LOGGER.warning("Function test already running")
            return
        self.test_stop = False
        # Set synchronously before the task exists - otherwise two
        # nearly simultaneous starts could create two tests.
        self.test_running = True
        try:
            self._test_task = self.hass.async_create_task(
                self._run_test(laufzeit_s, pause_s, einmalig)
            )
        except Exception:
            self.test_running = False
            raise

    async def _run_test(
        self, laufzeit_s: float, pause_s: float, einmalig: bool
    ) -> None:
        self.test_current_channel = 0
        _LOGGER.info(
            "Function test started: runtime=%.1fs, pause=%.2fs, once=%s",
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
            _LOGGER.info("Function test cancelled")
        except Exception as err:
            _LOGGER.error("Function test error: %s", err)
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
            _LOGGER.info("Function test finished")

    async def async_stop_test(self) -> None:
        self.test_stop = True
        task = self._test_task
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        self._test_task = None
        # Even a task cancelled before its first step must not leave the
        # running flag set (otherwise no test could ever start again).
        self.test_running = False
        self.test_current_channel = 0

    # ─────────────── Reset statistics ───────────────

    def reset_stats(self) -> None:
        connected = self.stats.get("verbunden", False)
        self.stats = _fresh_stats()
        self.stats["verbunden"] = connected
        now_mono = time.monotonic()
        for index in range(self.relay_count):
            self.channel_stats[index] = _fresh_channel_stats()
            self.channel_stats[index]["zustand"] = self.relay_states[index]
            self.channel_stats[index]["letzter_wechsel"] = now_mono
        self.async_set_updated_data(
            {"relay_states": self.relay_states, "stats": self.stats}
        )
        _LOGGER.info("Statistics reset")
        # first_seen deliberately survives: it is a board fact, not a statistic.
        with suppress(Exception):
            self.hass.async_create_task(self._async_persist())


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
