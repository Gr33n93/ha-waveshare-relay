"""Kompatibilitätsschicht für verschiedene pymodbus-Versionen.

pymodbus 3.6-3.8: slave=
pymodbus 3.9-3.10: slave= (unit= wirft Fehler)
pymodbus 3.11+: device_id= (slave= entfernt)
pymodbus 4.0+: device_id=
"""
from __future__ import annotations

import logging
from pymodbus.client import AsyncModbusTcpClient

_LOGGER = logging.getLogger(__name__)

# Wird beim ersten erfolgreichen Aufruf gesetzt
_UNIT_KWARG: str | None = None


async def read_coils_compat(
    client: AsyncModbusTcpClient,
    address: int,
    count: int,
    unit_id: int,
):
    """read_coils() kompatibel mit allen pymodbus-Versionen."""
    global _UNIT_KWARG

    if _UNIT_KWARG is not None:
        if _UNIT_KWARG == "__none__":
            return await client.read_coils(address, count=count)
        return await client.read_coils(address, count=count, **{_UNIT_KWARG: unit_id})

    # Reihenfolge: device_id (3.11+/4.x), slave (3.6-3.10), ohne
    for kwarg in ("device_id", "slave"):
        try:
            result = await client.read_coils(address, count=count, **{kwarg: unit_id})
            _UNIT_KWARG = kwarg
            _LOGGER.info("pymodbus nutzt '%s' als Unit-Parameter", kwarg)
            return result
        except TypeError:
            _LOGGER.debug("pymodbus akzeptiert '%s' nicht, versuche nächsten", kwarg)
            continue

    # Letzter Fallback: ohne Parameter
    _LOGGER.warning("pymodbus: weder 'device_id' noch 'slave' akzeptiert – nutze Default")
    _UNIT_KWARG = "__none__"
    return await client.read_coils(address, count=count)


async def write_coil_compat(
    client: AsyncModbusTcpClient,
    address: int,
    value: bool,
    unit_id: int,
):
    """write_coil() kompatibel mit allen pymodbus-Versionen."""
    global _UNIT_KWARG

    if _UNIT_KWARG is not None:
        if _UNIT_KWARG == "__none__":
            return await client.write_coil(address, value)
        return await client.write_coil(address, value, **{_UNIT_KWARG: unit_id})

    for kwarg in ("device_id", "slave"):
        try:
            result = await client.write_coil(address, value, **{kwarg: unit_id})
            _UNIT_KWARG = kwarg
            return result
        except TypeError:
            continue

    _UNIT_KWARG = "__none__"
    return await client.write_coil(address, value)
