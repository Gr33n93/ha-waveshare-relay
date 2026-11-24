# Waveshare Modbus PoE Ethernet Relay 1.2.0

### What changed

- The integration now supports English and German. Thanks to @sftgunner for the English localization in [#2](https://github.com/Gr33n93/ha-waveshare-relay/pull/2).
- When a poll fails after setup, the connection sensor reports `off` rather than `unavailable`. Relays still become `unavailable` until contact is restored. The outage notification examples in both READMEs now match this behavior.
- Frequently changing statistics, such as response time, now publish their first update immediately even just after a host reboot. Subsequent updates are still limited to once a minute.
- Timed relay pulses now work with pymodbus 3.16.2. At startup, the integration checks how the installed library encodes a pulse **without sending anything to the board**. If the check fails, it refuses the pulse and explains why. Normal switching, turning a channel off, and **All relays off** remain available.

### Automation compatibility

The **function-test status sensor** now reports `idle` or `running` in all languages. If an automation matched a German state such as `Läuft – Kanal 3`, match `running` and check the `aktueller_kanal` attribute for `3` instead. The channel mode selector still uses `Switch` and `Pulse`.

**Hinweis für bestehende Automationen:** Der Funktionstest-Sensor meldet jetzt `idle` oder `running`. Statt `Läuft – Kanal 3` bitte auf `running` und das Attribut `aktueller_kanal: 3` prüfen. Die Modusauswahl bleibt bei `Switch` und `Pulse`.

### Verification

Tested with Home Assistant Core 2026.11.3 and pymodbus 3.13.1 and 3.16.2. On a physical eight-channel Waveshare board, each channel was pulsed separately with pymodbus 3.16.2. In every case only the selected channel reported on, and the board reported all eight off again without a separate off command.
