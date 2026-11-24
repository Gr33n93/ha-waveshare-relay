# Waveshare Modbus PoE Ethernet Relay

[🇩🇪 Deutsch](README.de.md) | [🇬🇧 English](README.md)

[![Open in the Home Assistant Marketplace](https://img.shields.io/badge/Home%20Assistant-Marketplace-41BDF5?style=for-the-badge)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration)
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

## Install from the Marketplace

Starting with Home Assistant **2026.11**, the Marketplace is built in. You don't
need to install HACS separately.

1. As an administrator, open **Settings → Marketplace**. Before your first
   installation, accept the risk notice for community projects.
2. Search for **Waveshare Modbus PoE Ethernet Relay** and open the entry.
   Alternatively, [open the entry directly](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration).
3. Select **Install** and confirm the version shown.
4. Continue with [Setup](#setup). Restart Home Assistant only if the Marketplace
   prompts you to do so.

**Home Assistant 2026.10 and earlier:** Set up [HACS](https://www.hacs.xyz/docs/use/)
first if you haven't already. Open **HACS** in the sidebar, search for
**Waveshare Modbus PoE Ethernet Relay**, and download the integration. Then
restart Home Assistant and add the integration as described below.

## Setup

Enter the board's connection details in the setup dialog. If the dialog doesn't
open automatically, go to **Settings → Devices & services → Add integration**
and search for **Waveshare Modbus PoE Ethernet Relay**.

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

The function-test sensor now reports the raw states `idle` and `running`,
translated in the interface. Automations using the previous German state text
must be updated; the `aktueller_kanal` attribute contains the current channel.

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

When the integration loads, it builds and checks a Modbus message with a known
pulse duration **without sending anything to the board**. If the check fails,
turning on a pulse channel reports **“Pulse not sent”**. No substitute command
is sent. Channels in **Switch** mode, turning individual relays off and **All
relays off** remain available. After a library update, the check runs again the
next time the integration loads.

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

After successful setup, the **Connection** sensor reports `off` if a board
poll fails. The relays and other entities become **unavailable**. When a poll
succeeds again, the sensor reports `on` and the integration reads the relay
states from the board. No restart is needed. After reconnection, see **Last
error message** and **Last error time** for the technical details.

To find the entity ID, open **Settings → Devices & services → Waveshare Modbus
PoE Ethernet Relay**, select your device and open the **Connection** sensor
under **Diagnostic**. Copy the entity ID from the sensor settings.

This automation notifies you when the board has been unreachable for one
minute. Replace the example entity ID with the one you copied:

```yaml
automation:
  - alias: "Waveshare Relay connection monitor"
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.replace_with_your_connection_sensor
        to: "off"
        for: "00:01:00"
    action:
      - service: persistent_notification.create
        data:
          title: "Waveshare Relay offline"
          message: "The board has been unreachable for over a minute."
```

For phone notifications, replace `persistent_notification.create` with your
phone's `notify.mobile_app_<device>` action.

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
- See [docs/HARDWARE.md](docs/HARDWARE.md) for the verified register map,
  identification details and the board web UI.

## Support development

If this integration helps you, you can support my work with a coffee. Your
voluntary contribution helps fund development, maintenance, and testing with
real hardware.

[☕ Support me on Ko-fi](https://ko-fi.com/nilsarnold)
