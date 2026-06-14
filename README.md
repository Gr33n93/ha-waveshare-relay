# Waveshare PoE Ethernet Relay (8CH) für Home Assistant

Custom Integration für das Waveshare PoE Ethernet Relay Board mit 8 Kanälen.
Die Integration steuert das Board lokal per Modbus TCP und legt die Relais als
Home-Assistant-Entities an.

## Funktionen

- 8 Relais als `switch`-Entities
- Live-Status per Modbus FC01 Polling
- Schalten per Modbus FC05
- Verbindungsstatus als Diagnose-Entity
- Statistik für Abfragen, Schreibvorgänge, Fehler und Reaktionszeit
- Pro Kanal EIN-/AUS-Zähler und sessionbasierte EIN-/AUS-Dauer
- Funktionstest, der alle Kanäle nacheinander schaltet
- Service und Button für "Alle Relais aus"

## Installation mit HACS

1. HACS in Home Assistant öffnen.
2. **Integrations** öffnen.
3. Über das Drei-Punkte-Menü **Custom repositories** öffnen.
4. Repository eintragen:

   ```text
   https://github.com/Gr33n93/ha-waveshare-relay
   ```

5. Kategorie **Integration** wählen.
6. Integration installieren.
7. Home Assistant neu starten.

## Manuelle Installation

Den Ordner `custom_components/waveshare_relay/` in das Home-Assistant-
Config-Verzeichnis kopieren:

```text
<HA-Config>/
  custom_components/
    waveshare_relay/
      __init__.py
      binary_sensor.py
      button.py
      config_flow.py
      const.py
      coordinator.py
      manifest.json
      modbus_compat.py
      sensor.py
      services.yaml
      strings.json
      switch.py
      translations/
        de.json
```

Typische Pfade:

- HA OS / Supervised: `/config/custom_components/waveshare_relay/`
- Docker: `<dein-config-mount>/custom_components/waveshare_relay/`
- Home Assistant Core: `~/.homeassistant/custom_components/waveshare_relay/`

Danach Home Assistant neu starten.

## Einrichtung

Nach dem Neustart:

```text
Einstellungen -> Geräte & Dienste -> Integration hinzufügen -> Waveshare
```

Konfiguration:

- **IP-Adresse**: IP-Adresse des Relay-Boards
- **Port**: `502` für Modbus TCP
- **Unit-ID**: normalerweise `1`
- **Abfrageintervall**: Standard `2` Sekunden

Beim Speichern wird ein Verbindungstest durchgeführt. Wenn der Test erfolgreich
ist, werden die Entities automatisch angelegt.

## Entities

| Typ | Anzahl | Beschreibung |
| --- | ---: | --- |
| `switch` | 8 | Relais 1 bis 8 |
| `binary_sensor` | 1 | Verbindungsstatus |
| `sensor` | 10 | Globale Diagnose- und Statistikwerte |
| `sensor` | 40 | Kanalwerte für Dauer, Zähler und Schreibfehler |
| `sensor` | 1 | Funktionstest-Status |
| `button` | 4 | Funktionstest Start/Stop, Alle aus, Statistik zurücksetzen |

## Services

| Service | Beschreibung |
| --- | --- |
| `waveshare_relay.funktionstest_start` | Startet den Funktionstest |
| `waveshare_relay.funktionstest_stop` | Stoppt den Funktionstest und schaltet alle Relais aus |
| `waveshare_relay.statistik_zuruecksetzen` | Setzt Statistik- und Dauerwerte zurück |
| `waveshare_relay.alle_aus` | Schaltet alle 8 Relais aus |

Parameter für `funktionstest_start`:

| Parameter | Standard | Beschreibung |
| --- | ---: | --- |
| `laufzeit_s` | `5` | Einschaltdauer pro Relais |
| `pause_s` | `0.25` | Pause zwischen zwei Kanälen |
| `einmalig` | `true` | Ein Durchlauf oder Dauertest |

## Dashboard

Die Datei `lovelace_dashboard.yaml` enthält ein Beispiel-Dashboard mit vier
Ansichten:

- Relaissteuerung
- Statistik
- Kanaldetails
- Funktionstest

Die Entity-IDs können je nach Home-Assistant-Instanz abweichen. Falls eine Karte
nicht funktioniert, die tatsächlichen Entity-IDs unter **Geräte & Dienste** prüfen
und im Dashboard-YAML anpassen.

## Hinweise

- Das Board erlaubt typischerweise nur eine gleichzeitige Modbus-TCP-Verbindung.
  Andere Modbus-Adapter oder Testtools sollten nicht parallel verbunden sein.
- Die Dauerwerte werden sessionbasiert gezählt. Nach einem Home-Assistant-Neustart
  oder Statistik-Reset beginnen sie wieder bei `0`.
- `pymodbus` wird automatisch über die Integration installiert.
