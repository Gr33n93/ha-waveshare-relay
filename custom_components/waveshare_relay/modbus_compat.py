"""Compatibility layer for pymodbus coil I/O and native Waveshare pulses."""
from __future__ import annotations

from inspect import signature
import logging
import struct

from pymodbus.client import AsyncModbusTcpClient

try:
    from . import pulse as _pulse
except ImportError:  # Optional pulse APIs must not prevent normal relay setup.
    _pulse = None

_LOGGER = logging.getLogger(__name__)

# Set on the first call: "device_id", "slave" or "__none__"
# for pymodbus versions without a unit parameter.
_UNIT_KWARG: str | None = None


async def _call(client: AsyncModbusTcpClient, method: str, *args, unit_id: int, **kwargs):
    """Call a client method with a version-stable unit parameter."""
    global _UNIT_KWARG

    call = getattr(client, method)
    if _UNIT_KWARG is None:
        # Older clients silently swallow device_id in **kwargs and address unit 0.
        # Inspect before sending; never probe by retrying an actual coil write.
        params = signature(call).parameters
        _UNIT_KWARG = next((key for key in ("device_id", "slave") if key in params), "__none__")

    if _UNIT_KWARG == "__none__":
        return await call(*args, **kwargs)
    return await call(*args, **kwargs, **{_UNIT_KWARG: unit_id})


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


def pulse_encoding_supported(unit_id: int) -> bool:
    """Fail closed for pulses only if the installed TCP encoder cannot be verified."""
    if _pulse is None:
        _LOGGER.warning("Native relay pulses disabled: Modbus pulse encoder unavailable")
        return False
    try:
        frame = _pulse.probe_tcp_frame(unit_id)
        # MBAP (transaction 0, Modbus, length 6, unit), FC05, address, ticks.
        if frame == struct.pack(">HHHBBHH", 0, 0, 6, unit_id, 5, 0x0204, 5):
            return True
        _LOGGER.warning("Native relay pulses disabled: unexpected Modbus TCP test frame")
    except Exception as err:
        _LOGGER.warning("Native relay pulses disabled: cannot verify Modbus TCP encoding: %s", err)
    return False


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
    if _pulse is None:
        raise RuntimeError("Modbus pulse encoder unavailable")
    pdu = _pulse.WavesharePulseRequest(address, max(1, duration_ms // 100), unit_id)

    # Choose the call shape *before* sending: never retry a possibly sent pulse.
    try:
        signature(client.execute).bind(False, pdu)
    except TypeError:
        return await client.execute(pdu)  # pymodbus 3.6
    return await client.execute(False, pdu)
