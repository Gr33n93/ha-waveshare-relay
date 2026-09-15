# Hardware reference

Everything below was verified against real boards (8CH and 16CH) in
September 2026. It complements the [Waveshare wikis](https://www.waveshare.com/wiki/Modbus_POE_ETH_Relay)
with practical findings.

## Models

| Model | Relays | Ethernet ports | Web UI |
| --- | ---: | ---: | --- |
| Modbus POE ETH Relay | 8 | 1 | no |
| Modbus POE ETH Relay 16CH | 16 | 2 (transparent pass-through) | yes |
| Modbus POE ETH Relay 30CH | 30 | 2 (transparent pass-through) | yes |

## Modbus TCP

- Port `502`, unit ID `1` by default
- **Only one concurrent TCP connection** - other clients/tools must be
  disconnected while Home Assistant talks to the board

### Register map (verified)

| Address | Function code | Meaning |
| --- | --- | --- |
| `0x0000 + ch` | 01 / 05 | Relay state; write `0xFF00` on, `0x0000` off, `0x5500` toggle |
| `0x00FF` | 05 | All relays on/off |
| `0x0100 + ch` | 05 | Toggle single channel |
| `0x01FF` | 05 | Toggle all channels |
| `0x0200 + ch` | 05 | **Flash ON**: value = time in 100 ms steps (max `0x7FFF`) - board switches off by itself |
| `0x0400 + ch` | 05 | Flash OFF: same encoding |
| `0x4000` | 03 | Device address (unit ID) |
| `0x8000` | 03 | Software version (value / 100, e.g. `200` = V2.00) |

Reading coils **beyond the relay count** returns a Modbus exception -
this allows detecting the board model by probing count 30 → 16 → 8.

## Identification

- **No serial number register** exists
- **MAC address** is the only stable identity (Waveshare/ZLAN OUI
  `04:EE:E8`); it survives IP changes and is readable from the host ARP
  table. The integration uses it as the storage key for statistics
- Both Ethernet ports share one MAC; the second port is a transparent
  pass-through (a device behind it appears with its own MAC)

## Discovery behaviour

- No mDNS, no SSDP, no UDP discovery - the boards are silent on the
  network except for Modbus TCP and (16CH/30CH) HTTP

## Web UI (16CH / 30CH only)

- HTTP on port 80, default password `admin` (change it on first login)
- Shows/edits: device name (default `WSDEV0001`), MAC, firmware, IP
  settings (DHCP/static), work mode
