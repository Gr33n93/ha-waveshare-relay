"""Waveshare's timed FC05 request (not an ordinary boolean coil write)."""
from __future__ import annotations

import struct

try:  # pymodbus 3.8+
    from pymodbus.pdu.bit_message import WriteSingleCoilRequest
    _legacy_coil = False
except ImportError:
    try:  # 3.7
        from pymodbus.pdu.bit_write_message import WriteSingleCoilRequest
    except ImportError:  # 3.6
        from pymodbus.bit_write_message import WriteSingleCoilRequest
    _legacy_coil = True

try:
    from pymodbus.framer.socket import FramerSocket
    from pymodbus.pdu.decoders import DecodePDU
except ImportError:  # 3.6
    from pymodbus.factory import ClientDecoder
    from pymodbus.framer.socket_framer import ModbusSocketFramer

    def _frame(pdu):
        return ModbusSocketFramer(ClientDecoder()).buildPacket(pdu)
else:
    def _frame(pdu):
        return FramerSocket(DecodePDU(False)).buildFrame(pdu)


class WavesharePulseRequest(WriteSingleCoilRequest):
    """Encode the board's pulse duration in 100 ms ticks instead of ON/OFF."""

    def __init__(self, address: int, ticks: int, unit_id: int) -> None:
        if _legacy_coil:
            super().__init__(address=address, value=True, slave=unit_id)
        else:
            super().__init__(address=address, bits=[True], dev_id=unit_id)
        self.ticks = ticks

    def encode(self) -> bytes:
        return struct.pack(">HH", self.address, self.ticks)

    # Newer pymodbus framers dispatch through the decoder to x_encode.
    x_encode = encode


def probe_tcp_frame(unit_id: int) -> bytes:
    """Build a complete representative TCP request locally. No client or socket."""
    return _frame(WavesharePulseRequest(0x0204, 5, unit_id))
