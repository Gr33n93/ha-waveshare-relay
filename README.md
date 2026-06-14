# Waveshare PoE Ethernet Relay (8CH)

![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Integration-18BCF2?style=for-the-badge)
![Release](https://img.shields.io/github/v/release/Gr33n93/ha-waveshare-relay?style=for-the-badge)

Home-Assistant-Integration für das Waveshare PoE Ethernet Relay Board mit 8
Relais. Die Kommunikation läuft lokal per Modbus TCP.

## Überblick

| Bereich | Funktion |
| --- | --- |
| Relais | 8 Schalter für die Kanäle 1 bis 8 |
| Status | Live-Abfrage per Modbus FC01 |
| Schalten | Relaissteuerung per Modbus FC05 |
| Diagnose | Verbindung, Reaktionszeit, Fehler und Schreibzähler |
| Kanäle | EIN-/AUS-Zähler und sessionbasierte Laufzeiten |
| Wartung | Funktionstest, Statistik-Reset und "Alle Relais aus" |

## Installation über HACS

Diese Integration ist aktuell als benutzerdefiniertes HACS-Repository nutzbar.

```text
https://github.com/Gr33n93/ha-waveshare-relay
```

In HACS:

1. **HACS -> Integrationen** öffnen
2. **Custom repositories** öffnen
3. URL eintragen
4. Kategorie **Integration** auswählen
5. Integration installieren
6. Home Assistant neu starten

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

Beim Speichern führt Home Assistant einen Verbindungstest aus. Danach werden die
Entities automatisch angelegt.

## Entities

| Typ | Anzahl | Beschreibung |
| --- | ---: | --- |
| `switch` | 8 | Relais 1 bis 8 |
| `binary_sensor` | 1 | Verbindungsstatus |
| `sensor` | 51 | Statistik, Laufzeiten, Zähler und Teststatus |
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

`lovelace_dashboard.yaml` enthält ein Beispiel-Dashboard mit:

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
- `pymodbus` wird automatisch installiert.
