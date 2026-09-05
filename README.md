# Waveshare Modbus PoE Ethernet Relay

**English | [Deutsch](README.de.md)**

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5?style=for-the-badge)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2?style=for-the-badge)
![Release](https://img.shields.io/github/v/release/Gr33n93/ha-waveshare-relay?style=for-the-badge)

Home Assistant integration for Waveshare Modbus PoE Ethernet Relay boards. All
communication takes place locally over Modbus TCP.

## Supported devices

| Device | Relays |
| --- | ---: |
| Modbus POE ETH Relay | 8 |
| Modbus POE ETH Relay 16CH | 16 |
| Modbus POE ETH Relay 30CH | 30 |

## Overview

| Area | Function |
| --- | --- |
| Relays | Switches for all configured channels |
| Status | Live polling over Modbus FC01 |
| Control | Relay control over Modbus FC05 |
| Diagnostics | Connection, response time, errors, and write counters |
| Channels | On/off counters and session-based runtimes |
| Maintenance | Function test, statistics reset, and "All relays off" |

## Installation through HACS

This integration is included in the [HACS default repository](https://github.com/hacs/default/blob/master/integration)
and is available directly through HACS search.

Prerequisite: HACS must be installed and configured in Home Assistant.

Use this button to open the integration directly in HACS:

[![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration)

Alternatively, open HACS from the Home Assistant sidebar:

1. Search for **Waveshare Modbus PoE Ethernet Relay**.
2. Open the matching entry.
3. Select **Download** and confirm the download.
4. Restart Home Assistant.
5. Add the integration as described under [Setup](#setup).

## Setup

After restarting Home Assistant:

```text
Settings -> Devices & services -> Add integration -> Waveshare
```

Required information:

| Field | Value |
| --- | --- |
| IP address | IP address of the relay board |
| Port | `502` |
| Unit ID | Usually `1` |
| Polling interval | Default: `2` seconds |
| Number of relays | `8`, `16`, or `30` |

Home Assistant tests the connection when you save the configuration. It then
creates the entities automatically.

## Entities

| Type | Number | Description |
| --- | ---: | --- |
| `switch` | Number of relays | One switch per relay |
| `binary_sensor` | 1 | Connection status |
| `sensor` | 11 + 5 per relay | Statistics, runtimes, counters, and test status |
| `button` | 4 | Function test, all off, and statistics reset |

## Services

| Service | Description |
| --- | --- |
| `waveshare_relay.alle_aus` | Turns off all relays |
| `waveshare_relay.funktionstest_start` | Starts a channel function test |
| `waveshare_relay.funktionstest_stop` | Stops the function test |
| `waveshare_relay.statistik_zuruecksetzen` | Resets statistics |

Parameters for `funktionstest_start`:

| Parameter | Default | Description |
| --- | ---: | --- |
| `laufzeit_s` | `5` | On duration per channel |
| `pause_s` | `0.25` | Pause between channels |
| `einmalig` | `true` | Single run or continuous test |

## Dashboard

`lovelace_dashboard.yaml` contains an example dashboard for an 8-channel board
with:

- Relay controls
- Statistics
- Channel details
- Function test

Entity IDs may differ in your Home Assistant instance. If a card does not work,
check the actual entity IDs under **Devices & services** and update the dashboard
YAML accordingly.

## Manual installation

Alternatively, copy the integration folder manually:

```text
custom_components/waveshare_relay -> /config/custom_components/waveshare_relay
```

Restart Home Assistant afterward.

## Notes

- The board typically permits only one simultaneous Modbus TCP connection.
- Do not connect other Modbus adapters or test tools at the same time.
- Runtime values are session-based and restart from zero after a restart or
  reset.
- RS485/RTU boards such as the Modbus RTU Relay 4CH are not supported.
- The integration uses the Modbus library provided by Home Assistant's built-in
  Modbus integration.

## Support development

If this integration helps you, you can support my work with a coffee. Your
voluntary contribution helps fund development, maintenance, and testing with
real hardware.

[☕ Support me on Ko-fi](https://ko-fi.com/nilsarnold)
