# Waveshare Modbus PoE Ethernet Relay

[🇩🇪 Deutsch](README.de.md) | [🇬🇧 English](README.md)

![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2?style=for-the-badge)
![Release](https://img.shields.io/github/v/release/Gr33n93/ha-waveshare-relay?style=for-the-badge)

Home Assistant integration for Waveshare Modbus PoE Ethernet relay boards.
Communication runs locally over Modbus TCP.

## Supported devices

| Device | Relays |
| --- | ---: |
| Modbus POE ETH Relay | 8 |
| Modbus POE ETH Relay 16CH | 16 |
| Modbus POE ETH Relay 30CH | 30 |

## Overview

| Area | Function |
| --- | --- |
| Relays | Switch entities for every configured channel |
| State | Live polling via Modbus FC01 |
| Switching | Relay control via Modbus FC05 |
| Diagnostics | Connection, response time, errors and write counters |
| Channels | On/off counters and session-based duty times |
| Maintenance | Function test, statistics reset and "all relays off" |

## Installation via HACS

This integration is available as a custom HACS repository.

```text
https://github.com/Gr33n93/ha-waveshare-relay
```

In HACS:

1. Open **HACS -> Integrations**
2. Open **Custom repositories**
3. Enter the URL
4. Choose category **Integration**
5. Install the integration
6. Restart Home Assistant

## Setup

After the restart, in Home Assistant:

```text
Settings -> Devices & Services -> Add Integration -> Waveshare
```

Required data:

| Field | Value |
| --- | --- |
| IP address | IP address of the relay board |
| Port | `502` |
| Unit ID | usually `1` |
| Poll interval | default `2` seconds |
| Relay count | `8`, `16` or `30` |

On submit Home Assistant runs a connection test, then the entities are
created automatically.

## Entities

| Type | Count | Description |
| --- | ---: | --- |
| `switch` | relay count | One switch per relay (mode: Switch or Pulse) |
| `select` | relay count | Mode selector (Switch/Pulse), in the control section next to each channel |
| `binary_sensor` | 1 | Connection status |
| `sensor` | 12 + 5 per relay | Statistics, duty times, counters and test status |
| `button` | 4 | Function test, all off, reset statistics |

## Per-channel mode (Switch / Pulse)

Every channel is configurable individually through the integration options
(**Devices & Services -> Waveshare Relay -> Configure**) or directly via the
mode select: display name, mode and pulse duration.

- **Switch**: regular on/off switching; the entity reflects the real board
  state.
- **Pulse**: turning on triggers the native Waveshare pulse command
  (Modbus FC05 at address `0x0200 + channel`, time in 100 ms steps). The
  board switches back off by itself after the configured duration - even
  if Home Assistant is unreachable in between. Intended for bistable
  relays and impulse switches. Turning off safely ends a running pulse.

Changing the mode changes neither name, entity ID nor unique ID -
dashboards and automations keep working. Additional attributes
(`betriebsart` with `switch`/`pulse`, `impulsdauer_ms`, `letzter_impuls`)
expose the current configuration.

### Mode directly on the device / dashboard

Besides the options dialog, every channel has a select entity
(`select.*_mode`, shown as "Relais N Mode") to switch between Switch and
Pulse directly - on the device page in the **control** section right next
to the channel, or as a dashboard card (see `lovelace_dashboard.yaml`).
Changing the mode via the select behaves exactly like the options dialog:
it is persisted and survives restarts.

## Services

| Service | Description |
| --- | --- |
| `waveshare_relay.alle_aus` | Switches all relays off |
| `waveshare_relay.funktionstest_start` | Starts a channel function test |
| `waveshare_relay.funktionstest_stop` | Stops the function test |
| `waveshare_relay.statistik_zuruecksetzen` | Resets statistics values |

All services accept an optional **target device** (device selector).
Without a target they act on all configured boards - existing automations
keep behaving exactly as before.

Parameters for `funktionstest_start`:

| Parameter | Default | Description |
| --- | ---: | --- |
| `laufzeit_s` | `5` | On time per channel |
| `pause_s` | `0.25` | Pause between channels |
| `einmalig` | `true` | Single pass or continuous test |
| `device_id` | – | Optional: board the test runs on |

While a function test is running, manual switch commands are blocked so
they cannot interleave with the test sequence. `alle_aus` remains
available at all times as a safety stop.

## Connection monitoring

When the board disappears (power or network loss), all entities of the
device go **unavailable** and the **connection** binary sensor
(`binary_sensor.*_verbindung`) turns **off**. As soon as the board is
reachable again the integration reconnects automatically - no restart
required. The last error is available in the diagnostic sensors "Letzte
Fehlermeldung" and "Letzter Fehler (Zeit)".

Active notifications are up to you - a ready-to-use example (notify when
the board has been gone for more than a minute):

```yaml
automation:
  - alias: "Waveshare Relay connection monitor"
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.waveshare_relay_verbindung
        to: "off"
        for: "00:01:00"
    action:
      - service: notify.persistent_notification
        data:
          title: "Waveshare Relay offline"
          message: "The board has been unreachable for over a minute."
```

For phone notifications replace `notify.persistent_notification` with
`notify.mobile_app_<device>`. The actual entity ID may differ depending
on your device name - search for `verbindung` under **Developer Tools ->
States**.

Note: pulse channels (mode "Pulse") are never re-triggered automatically
on reconnection; regular channels show the actual board state after
reconnecting.

## Dashboard

`lovelace_dashboard.yaml` contains an example dashboard for an 8CH board
with:

- Relay control
- Statistics
- Channel details
- Function test

Entity IDs may differ in your Home Assistant instance. If a card does not
work, look up the actual entity IDs under **Devices & Services** and
adjust the dashboard YAML.

## Manual installation

Alternatively, copy the folder manually:

```text
custom_components/waveshare_relay -> /config/custom_components/waveshare_relay
```

Then restart Home Assistant.

## Notes

- The board typically allows only one concurrent Modbus TCP connection.
- Other Modbus clients or test tools should not be connected in parallel.
- Statistics are persisted per board (keyed by MAC) and survive restarts,
  reloads and even deleting/re-adding the board. Only the reset button zeroes
  the counters; the first connection date is kept (sensor "Erste Verbindung" -
  shows the board aging).
- Duration sensors advance on every relay change; the currently running
  value is available as attribute `aktuell_s`.
- RS485/RTU boards such as the Modbus RTU Relay 4CH are not supported.
- The integration uses the Modbus library that Home Assistant provides
  through the built-in Modbus integration.
