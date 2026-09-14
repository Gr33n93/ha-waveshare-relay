"""Compatibility layer for various pymodbus versions.

pymodbus 3.6-3.8: slave=
pymodbus 3.9-3.10: slave= (unit= raises)
pymodbus 3.11+: device_id= (slave= removed)
pymodbus 4.0+: device_id=

The unit parameter is detected once and cached module-wide; every call
goes through _call(), so version handling lives in exactly one place.
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

# Set on the first successful call: "device_id", "slave" or "__none__"
# for pymodbus versions without a unit parameter.
_UNIT_KWARG: str | None = None


async def _call(client: AsyncModbusTcpClient, method: str, *args, unit_id: int, **kwargs):
    """Call a client method with a version-stable unit parameter."""
    global _UNIT_KWARG

    if _UNIT_KWARG is None:
        for kwarg in ("device_id", "slave"):
            try:
                result = await getattr(client, method)(*args, **kwargs, **{kwarg: unit_id})
                _UNIT_KWARG = kwarg
                _LOGGER.info("pymodbus uses '%s' as unit parameter", kwarg)
                return result
            except TypeError:
                _LOGGER.debug("pymodbus does not accept '%s', trying next", kwarg)
        _LOGGER.warning(
            "pymodbus accepts neither 'device_id' nor 'slave' - using default"
        )
        _UNIT_KWARG = "__none__"

    if _UNIT_KWARG == "__none__":
        return await getattr(client, method)(*args, **kwargs)
    return await getattr(client, method)(*args, **kwargs, **{_UNIT_KWARG: unit_id})


async def read_coils_compat(
    client: AsyncModbusTcpClient,
    address: int,
    count: int,
    unit_id: int,
):
    """read_coils() compatible with all pymodbus versions."""
    return await _call(client, "read_coils", address, count=count, unit_id=unit_id)


async def write_coil_compat(
    client: AsyncModbusTcpClient,
    address: int,
    value: bool,
    unit_id: int,
):
    """write_coil() compatible with all pymodbus versions."""
    return await _call(client, "write_coil", address, value, unit_id=unit_id)


def _build_pulse_pdu(address: int, ticks: int, unit_id: int):
    """Build a WriteSingleCoil PDU carrying the pulse time as value.

    Waveshare special form: FC05 at 0x0200+channel, where the value
    field does not carry 0xFF00/0x0000 but the pulse time in 100 ms
    ticks. pymodbus only encodes boolean values, so the value field is
    replaced after building the PDU.
    """
    for kwargs in ({"dev_id": unit_id}, {"device_id": unit_id}, {"slave": unit_id}):
        try:
            pdu = WriteSingleCoilRequest(address=address, bits=[True], **kwargs)
            break
        except TypeError:
            continue
    else:
        # pymodbus 3.6-3.8: value= instead of bits=
        pdu = WriteSingleCoilRequest(address=address, value=True)

    pdu.encode = lambda: struct.pack(">HH", address, ticks)
    return pdu


async def write_pulse_compat(
    client: AsyncModbusTcpClient,
    address: int,
    duration_ms: int,
    unit_id: int,
):
    """Trigger the native Waveshare pulse (FC05 with a time value).

    The board switches back off by itself when the time elapses,
    independent of Home Assistant. Returns like write_coil().
    """
    ticks = max(1, duration_ms // 100)
    pdu = _build_pulse_pdu(address, ticks, unit_id)

    # pymodbus 3.9+: execute(no_response_expected, pdu); 3.6-3.8: execute(pdu)
    try:
        return await client.execute(False, pdu)
    except TypeError:
        return await client.execute(pdu)
