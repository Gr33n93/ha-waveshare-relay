"""Kompatibilitätsschicht für verschiedene pymodbus-Versionen.

pymodbus 3.6-3.8: slave=
pymodbus 3.9-3.10: slave= (unit= wirft Fehler)
pymodbus 3.11+: device_id= (slave= entfernt)
pymodbus 4.0+: device_id=
"""
from __future__ import annotations

import logging
import struct

from pymodbus.client import AsyncModbusTcpClient

try:  # pymodbus >= 3.9
    from pymodbus.pdu.bit_message import WriteSingleCoilRequest
except ImportError:  # pymodbus 3.6-3.8
    from pymodbus.bit_write_message import WriteSingleCoilRequest  # noqa: F401

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


def _build_pulse_pdu(address: int, ticks: int, unit_id: int):
    """WriteSingleCoil-PDU mit Impulszeit als Wertfeld erzeugen.

    Waveshare-Spezialform: FC05 an 0x0200+Kanal, wobei das eigentliche
    Wertfeld nicht 0xFF00/0x0000 trägt, sondern die Impulszeit in
    100-ms-Ticks. pymodbus kodiert nur Bool-Werte, deshalb wird das
    Wertfeld nach dem Aufbau der PDU gesetzt.
    """
    pdu = None
    # Reihenfolge wie read/write_coil_compat: neue Kwargs zuerst
    for kwargs in ({"dev_id": unit_id}, {"device_id": unit_id}, {"slave": unit_id}):
        try:
            pdu = WriteSingleCoilRequest(address=address, bits=[True], **kwargs)
            break
        except TypeError:
            continue
    if pdu is None:
        # pymodbus 3.6-3.8: value= statt bits=
        try:
            pdu = WriteSingleCoilRequest(address=address, value=True)
        except TypeError as err:
            raise RuntimeError(
                "pymodbus WriteSingleCoilRequest nicht nutzbar"
            ) from err

    pdu.encode = lambda: struct.pack(">HH", address, ticks)
    return pdu


async def write_pulse_compat(
    client: AsyncModbusTcpClient,
    address: int,
    duration_ms: int,
    unit_id: int,
):
    """Waveshare-nativen Impuls auslösen (FC05 mit Zeitwert).

    Das Board schaltet nach Ablauf der Zeit selbstständig zurück –
    unabhängig von Home Assistant. Rückgabe wie write_coil().
    """
    ticks = max(1, duration_ms // 100)
    pdu = _build_pulse_pdu(address, ticks, unit_id)

    # pymodbus 3.9+: execute(no_response_expected, pdu); 3.6-3.8: execute(pdu)
    try:
        return await client.execute(False, pdu)
    except TypeError:
        return await client.execute(pdu)
