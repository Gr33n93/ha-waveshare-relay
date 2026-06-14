"""Config Flow für Waveshare PoE Relay."""
from __future__ import annotations

import logging
from contextlib import suppress

import voluptuous as vol
from pymodbus.client import AsyncModbusTcpClient

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    CONF_UNIT_ID,
    CONF_POLL_INTERVAL,
    CONF_RELAY_COUNT,
    DEFAULT_PORT,
    DEFAULT_UNIT_ID,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RELAY_COUNT,
    SUPPORTED_RELAY_COUNTS,
)
from .modbus_compat import read_coils_compat

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
