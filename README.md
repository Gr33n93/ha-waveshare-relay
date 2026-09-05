# Waveshare Modbus PoE Ethernet Relay

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5?style=for-the-badge)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2?style=for-the-badge)
![Release](https://img.shields.io/github/v/release/Gr33n93/ha-waveshare-relay?style=for-the-badge)

Home-Assistant-Integration für Waveshare Modbus PoE Ethernet Relay Boards. Die
Kommunikation läuft lokal per Modbus TCP.

## Unterstützte Geräte

| Gerät | Relais |
| --- | ---: |
| Modbus POE ETH Relay | 8 |
| Modbus POE ETH Relay 16CH | 16 |
| Modbus POE ETH Relay 30CH | 30 |

## Überblick

| Bereich | Funktion |
| --- | --- |
| Relais | Schalter für alle konfigurierten Kanäle |
| Status | Live-Abfrage per Modbus FC01 |
| Schalten | Relaissteuerung per Modbus FC05 |
| Diagnose | Verbindung, Reaktionszeit, Fehler und Schreibzähler |
| Kanäle | EIN-/AUS-Zähler und sessionbasierte Laufzeiten |
| Wartung | Funktionstest, Statistik-Reset und "Alle Relais aus" |

## Installation über HACS

Diese Integration ist im [HACS-Standardverzeichnis](https://github.com/hacs/default/blob/master/integration)
enthalten und direkt über die HACS-Suche verfügbar.

Voraussetzung: HACS ist in Home Assistant installiert und eingerichtet.

Mit diesem Button öffnest du die Integration direkt in HACS:

[![Integration in HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration)

Oder öffne HACS über die Seitenleiste in Home Assistant:

1. Nach **Waveshare Modbus PoE Ethernet Relay** suchen.
2. Den passenden Eintrag öffnen.
3. **Herunterladen / Download** auswählen und den Download bestätigen.
4. Home Assistant neu starten.
5. Die Integration wie unter [Einrichtung](#einrichtung) beschrieben hinzufügen.

## Einrichtung

Nach dem Neustart in Home Assistant:

```text
Einstellungen -> Geräte & Dienste -> Integration hinzufügen -> Waveshare
```

Benötigte Daten:

| Feld | Wert |
| --- | --- |
| IP-Adresse | IP-Adresse des Relay-Boards |
| Port | `502` |
| Unit-ID | meistens `1` |
| Abfrageintervall | Standard `2` Sekunden |
| Relaisanzahl | `8`, `16` oder `30` |

Beim Speichern führt Home Assistant einen Verbindungstest aus. Danach werden die
Entities automatisch angelegt.

## Entities

| Typ | Anzahl | Beschreibung |
| --- | ---: | --- |
| `switch` | Relaisanzahl | Ein Schalter pro Relais |
| `binary_sensor` | 1 | Verbindungsstatus |
| `sensor` | 11 + 5 pro Relais | Statistik, Laufzeiten, Zähler und Teststatus |
| `button` | 4 | Funktionstest, Alle aus, Statistik zurücksetzen |

## Services

| Service | Beschreibung |
| --- | --- |
| `waveshare_relay.alle_aus` | Schaltet alle Relais aus |
| `waveshare_relay.funktionstest_start` | Startet einen Kanal-Funktionstest |
| `waveshare_relay.funktionstest_stop` | Stoppt den Funktionstest |
| `waveshare_relay.statistik_zuruecksetzen` | Setzt Statistikwerte zurück |

Parameter für `funktionstest_start`:

| Parameter | Standard | Beschreibung |
| --- | ---: | --- |
| `laufzeit_s` | `5` | Einschaltdauer pro Kanal |
| `pause_s` | `0.25` | Pause zwischen Kanälen |
| `einmalig` | `true` | Ein Durchlauf oder Dauertest |

## Dashboard

`lovelace_dashboard.yaml` enthält ein Beispiel-Dashboard für ein 8CH-Board mit:

- Relaissteuerung
- Statistik
- Kanaldetails
- Funktionstest

Die Entity-IDs können in deiner Home-Assistant-Instanz abweichen. Falls eine
Karte nicht funktioniert, die tatsächlichen Entity-IDs unter **Geräte & Dienste**
prüfen und im Dashboard-YAML anpassen.

## Manuelle Installation

Alternativ kann der Ordner manuell kopiert werden:

```text
custom_components/waveshare_relay -> /config/custom_components/waveshare_relay
```

Danach Home Assistant neu starten.

## Hinweise

- Das Board erlaubt typischerweise nur eine gleichzeitige Modbus-TCP-Verbindung.
- Andere Modbus-Adapter oder Testtools sollten nicht parallel verbunden sein.
- Laufzeitwerte werden sessionbasiert gezählt und nach Neustart oder Reset neu
  begonnen.
- RS485/RTU-Boards wie das Modbus RTU Relay 4CH werden nicht unterstützt.
- Die Integration nutzt die Modbus-Bibliothek, die Home Assistant über die
  eingebaute Modbus-Integration bereitstellt.

## Entwicklung unterstützen

Wenn dir diese Integration hilft, kannst du meine Arbeit mit einem Kaffee
unterstützen. Dein freiwilliger Beitrag hilft bei Weiterentwicklung, Pflege und
Tests mit echter Hardware.

[☕ Auf Ko-fi unterstützen](https://ko-fi.com/nilsarnold)
