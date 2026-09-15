"""Tests for the pymodbus compatibility layer and the pulse encoding."""
import asyncio
import struct

import pytest

from custom_components.waveshare_relay import modbus_compat as mc


class DeviceIdClient:
    """Stub speaking the modern signature (pymodbus 3.11+/4.x)."""

    async def read_coils(self, address, count=None, device_id=None):
        return ("device_id", address, count, device_id)


class SlaveOnlyClient:
    """Stub that only accepts slave= (pymodbus 3.6-3.10)."""

    async def read_coils(self, address, count=None, slave=None):
        return ("slave", address, count, slave)


class NoUnitClient:
    """Stub accepting no unit keyword at all."""

    async def read_coils(self, address, count=None):
        return ("none", address, count)


@pytest.fixture(autouse=True)
def reset_detection():
    mc._UNIT_KWARG = None
    yield
    mc._UNIT_KWARG = None


async def test_call_detects_device_id():
    result = await mc._call(DeviceIdClient(), "read_coils", 0, count=8, unit_id=1)
    assert result == ("device_id", 0, 8, 1)
    assert mc._UNIT_KWARG == "device_id"


async def test_call_falls_back_to_slave():
    result = await mc._call(SlaveOnlyClient(), "read_coils", 3, count=2, unit_id=5)
    assert result == ("slave", 3, 2, 5)
    assert mc._UNIT_KWARG == "slave"


async def test_call_survives_without_unit_parameter():
    result = await mc._call(NoUnitClient(), "read_coils", 0, count=1, unit_id=1)
    assert result == ("none", 0, 1)
    assert mc._UNIT_KWARG == "__none__"


async def test_detection_is_cached_after_first_call():
    client = DeviceIdClient()
    await mc._call(client, "read_coils", 0, count=1, unit_id=1)
    assert mc._UNIT_KWARG == "device_id"
    # Further calls go straight through the cached kwarg - probing
    # happens exactly once per process.
    await mc._call(client, "read_coils", 7, count=2, unit_id=3)
    assert mc._UNIT_KWARG == "device_id"


def test_pulse_pdu_carries_ticks_as_value():
    pdu = mc._build_pulse_pdu(0x0204, 5, 1)
    assert pdu.encode() == struct.pack(">HH", 0x0204, 5)


@pytest.mark.parametrize(
    ("duration_ms", "ticks"), [(500, 5), (50, 1), (10000, 100), (1234, 12)]
)
async def test_wire_format_normal_write_and_pulse(duration_ms, ticks):
    """Full round trip against a local Modbus TCP echo server."""
    captured: list[bytes] = []

    class EchoModbus(asyncio.Protocol):
        def connection_made(self, transport):
            self.transport = transport
            self.buf = b""

        def data_received(self, data):
            self.buf += data
            while len(self.buf) >= 7:
                tid, pid, length = struct.unpack(">HHH", self.buf[:6])
                if len(self.buf) < 6 + length:
                    break
                frame = self.buf[: 6 + length]
                self.buf = self.buf[6 + length :]
                unit, request = frame[6], frame[7:]
                captured.append(request)
                response = request if request[0] == 0x05 else bytes([0x01, 1, 0])
                self.transport.write(
                    struct.pack(">HHHB", tid, pid, len(response) + 1, unit) + response
                )

    loop = asyncio.get_running_loop()
    server = await loop.create_server(EchoModbus, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    from pymodbus.client import AsyncModbusTcpClient

    client = AsyncModbusTcpClient(host="127.0.0.1", port=port, timeout=3, retries=0)
    assert await client.connect()
    try:
        mc._UNIT_KWARG = None
        assert not (await mc.read_coils_compat(client, 0, 8, 1)).isError()

        assert not (await mc.write_coil_compat(client, 3, True, 1)).isError()
        fc, addr, value = captured[-1][0], *struct.unpack(">HH", captured[-1][1:5])
        assert (fc, addr, value) == (5, 3, 0xFF00)

        assert not (
            await mc.write_pulse_compat(client, 0x0204, duration_ms, 1)
        ).isError()
        fc, addr, value = captured[-1][0], *struct.unpack(">HH", captured[-1][1:5])
        assert (fc, addr, value) == (5, 0x0204, ticks)
    finally:
        client.close()
        server.close()
        await server.wait_closed()
