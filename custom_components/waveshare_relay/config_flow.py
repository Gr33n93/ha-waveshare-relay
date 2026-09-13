"""Config Flow für Waveshare PoE Relay."""
from __future__ import annotations

import logging
from contextlib import suppress

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectOptionDict,
    TextSelector,
)

from .const import (
    DOMAIN,
    CONF_UNIT_ID,
    CONF_POLL_INTERVAL,
    CONF_RELAY_COUNT,
    CONF_CHANNEL,
    CONF_CHANNEL_CONFIGS,
    CONF_CHANNEL_MODE,
    CONF_CHANNEL_NAME,
    CONF_PULSE_DURATION,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RELAY_COUNT,
    MAX_PULSE_DURATION_MS,
    MIN_PULSE_DURATION_MS,
    PULSE_STEP_MS,
    MODE_PULSE,
    MODE_SWITCH,
    SUPPORTED_RELAY_COUNTS,
)
from .modbus_compat import read_coils_compat
from .models import ChannelMode

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.All(
            int, vol.Range(min=1, max=65535)
        ),
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): vol.All(
            int, vol.Range(min=1, max=247)
        ),
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            int, vol.Range(min=1, max=10)
        ),
        vol.Required(CONF_RELAY_COUNT, default=DEFAULT_RELAY_COUNT): vol.All(
            vol.Coerce(int), vol.In(SUPPORTED_RELAY_COUNTS)
        ),
    }
)


class WaveshareRelayConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow: Verbindungsdaten + Verbindungstest."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> WaveshareRelayOptionsFlowHandler:
        """Options-Flow-Handler erzeugen."""
        return WaveshareRelayOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Schritt 1: Verbindungsdaten eingeben."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = user_input[CONF_PORT]
            unit_id = user_input[CONF_UNIT_ID]
            relay_count = user_input[CONF_RELAY_COUNT]

            if not host:
                errors["base"] = "invalid_host"
            else:
                client: AsyncModbusTcpClient | None = None
                try:
                    client = AsyncModbusTcpClient(host=host, port=port, timeout=3)
                    connected = await client.connect()
                    if not connected:
                        raise ConnectionError("Keine Verbindung")
                    result = await read_coils_compat(
                        client, address=0, count=relay_count, unit_id=unit_id
                    )
                    if result.isError():
                        raise ConnectionError(f"Modbus-Fehler: {result}")
                except Exception as err:
                    _LOGGER.error("Verbindungstest fehlgeschlagen: %s", err)
                    errors["base"] = "cannot_connect"
                else:
                    unique_id = f"waveshare_relay_{host}_{port}_{unit_id}"
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Waveshare Relay ({host}:{port} Unit {unit_id})",
                        data={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_UNIT_ID: unit_id,
                            CONF_POLL_INTERVAL: user_input[CONF_POLL_INTERVAL],
                            CONF_RELAY_COUNT: relay_count,
                        },
                    )
                finally:
                    if client is not None:
                        with suppress(Exception):
                            client.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )


class WaveshareRelayOptionsFlowHandler(config_entries.OptionsFlow):
    """Options-Flow: Kanäle einzeln bearbeiten (Name, Betriebsart, Impulsdauer).

    Der Moduswechsel ändert weder Entity-ID noch Unique-ID – Dashboards
    und Automationen bleiben beim Umschalten unverändert.
    """

    def __init__(self) -> None:
        """Gewählten Kanal zwischen den Schritten merken."""
        self._channel: int = 0

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Schritt 1: Kanal auswählen."""
        if user_input is not None:
            self._channel = int(user_input[CONF_CHANNEL])
            return await self.async_step_channel()

        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        choices = []
        for cfg in coordinator.channel_configs:
            art = "Impuls" if cfg.mode == ChannelMode.PULSE else "Dauerbetrieb"
            choices.append(
                SelectOptionDict(
                    value=str(cfg.channel),
                    label=f"Kanal {cfg.channel + 1} – {cfg.name} ({art})",
                )
            )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHANNEL): SelectSelector(
                        SelectSelectorConfig(options=choices)
                    )
                }
            ),
        )

    async def async_step_channel(
        self, user_input: dict | None = None
    ) -> FlowResult:
        """Schritt 2: Gewählten Kanal konfigurieren."""
        coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]
        config = coordinator.channel_configs[self._channel]
        errors: dict[str, str] = {}

        if user_input is not None:
            stored = dict(self.config_entry.options.get(CONF_CHANNEL_CONFIGS, {}))
            stored[str(self._channel)] = {
                "name": str(user_input[CONF_CHANNEL_NAME]).strip() or config.name,
                "mode": user_input[CONF_CHANNEL_MODE],
                "pulse_duration_ms": user_input[CONF_PULSE_DURATION],
            }
            return self.async_create_entry(
                title="",
                data={CONF_CHANNEL_CONFIGS: stored},
            )

        return self.async_show_form(
            step_id="channel",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CHANNEL_NAME, default=config.name): TextSelector(),
                    vol.Required(
                        CONF_CHANNEL_MODE, default=str(config.mode)
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=MODE_SWITCH, label="Dauerbetrieb"),
                                SelectOptionDict(value=MODE_PULSE, label="Impuls"),
                            ]
                        )
                    ),
                    vol.Required(
                        CONF_PULSE_DURATION, default=config.pulse_duration_ms
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_PULSE_DURATION_MS,
                            max=MAX_PULSE_DURATION_MS,
                            step=PULSE_STEP_MS,
                            unit_of_measurement="ms",
                            mode=NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"channel_number": str(self._channel + 1)},
        )
