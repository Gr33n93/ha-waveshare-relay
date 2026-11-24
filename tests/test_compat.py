"""Tests for the pymodbus compatibility layer and the pulse encoding."""
import asyncio
import socket
import struct
from unittest.mock import AsyncMock

import pytest

from custom_components.waveshare_relay import modbus_compat as mc
from custom_components.waveshare_relay.pulse import WavesharePulseRequest


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


async def test_legacy_client_with_extra_kwargs_receives_configured_unit():
    class LegacyClient:
        async def write_coil(self, address, value, slave=0, **kwargs):
            return address, value, slave

    assert await mc.write_coil_compat(LegacyClient(), 4, False, 17) == (4, False, 17)


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


def test_pulse_self_check_needs_no_socket(monkeypatch):
    def forbid_socket(*args, **kwargs):
        pytest.fail("Local pulse check attempted to create a socket")

    monkeypatch.setattr(socket, "socket", forbid_socket)
    assert mc.pulse_encoding_supported(17)


@pytest.mark.parametrize("hook", ["encode", "x_encode"])
def test_pulse_encoders_carry_ticks_as_value(hook):
    pdu = WavesharePulseRequest(0x0204, 5, 17)
    assert getattr(pdu, hook)() == struct.pack(">HH", 0x0204, 5)


async def test_no_second_pulse_if_execute_itself_raises_type_error():
    client = AsyncMock()
    client.execute.side_effect = TypeError("error after dispatch")
    with pytest.raises(TypeError, match="after dispatch"):
        await mc.write_pulse_compat(client, 0x0204, 500, 17)
    client.execute.assert_awaited_once()


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
                captured.append(bytes([unit]) + request)
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
        unit_id = 17
        assert not (await mc.read_coils_compat(client, 0, 8, unit_id)).isError()

        assert not (await mc.write_coil_compat(client, 3, True, unit_id)).isError()
        assert captured[-1] == struct.pack(">BBHH", unit_id, 5, 3, 0xFF00)

        assert not (
            await mc.write_pulse_compat(client, 0x0204, duration_ms, unit_id)
        ).isError()
        assert captured[-1] == struct.pack(">BBHH", unit_id, 5, 0x0204, ticks)
        assert not (await mc.write_coil_compat(client, 4, False, unit_id)).isError()
        assert captured[-1] == struct.pack(">BBHH", unit_id, 5, 4, 0)
    finally:
        client.close()
        server.close()
        await server.wait_closed()
