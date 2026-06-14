# Waveshare PoE Ethernet Relay (8CH) – Home Assistant Integration

## Was wird erzeugt?

| Entity-Typ       | Anzahl | Beschreibung                                          |
|-------------------|--------|-------------------------------------------------------|
| `switch`          | 8      | Relais 1–8 (ein/aus, live-Status alle 2s)             |
| `binary_sensor`   | 1      | Verbindungsstatus zum Board                           |
| `sensor`          | 10     | Globale Statistik (Abfragen, Schreiben, Fehler, etc.) |
| `sensor`          | 40     | Pro Kanal: EIN/AUS-Dauer + EIN/AUS/Fehler-Zähler     |
| `sensor`          | 1      | Funktionstest-Status                                  |
| **Services**      | 4      | Funktionstest Start/Stop, Statistik-Reset, Alle-Aus   |

## Installation

### Variante A: HACS Custom Repository

1. Dieses Repository in GitHub veröffentlichen.
2. In Home Assistant HACS öffnen.
3. **Integrations → Drei Punkte → Custom repositories** öffnen.
4. Repository-URL eintragen und Kategorie **Integration** wählen.
5. Integration über HACS installieren.
6. Home Assistant neu starten.

### Variante B: Manuelle Installation

#### 1. Dateien kopieren

Den Ordner `custom_components/waveshare_relay/` in dein HA Config-Verzeichnis kopieren:

```
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

Typischer Pfad:
- **HA OS / Supervised**: `/config/custom_components/waveshare_relay/`
- **Docker**: Gemountetes Config-Verzeichnis → `./config/custom_components/waveshare_relay/`
- **Core**: `~/.homeassistant/custom_components/waveshare_relay/`

#### 2. Home Assistant neustarten

### Integration hinzufügen

**Einstellungen → Geräte & Dienste → + Integration → "Waveshare"** suchen

Eingabefelder:
- **IP-Adresse**: z.B. `192.168.178.90`
- **Port**: `502` (Standard Modbus-TCP)
- **Unit-ID**: `1` (Standard)
- **Abfrageintervall**: `2` Sekunden

→ Es wird sofort ein Verbindungstest durchgeführt. Bei Erfolg werden alle Entities angelegt.

### Dashboard einrichten

Die Datei `lovelace_dashboard.yaml` enthält ein fertiges 4-View-Dashboard:
1. **Relais** – 8 Toggle-Buttons + Notaus
2. **Statistik** – Zähler, Reaktionszeit-Graph, Fehlermeldungen
3. **Kanaldetails** – EIN/AUS-Dauer und Zähler pro Relais
4. **Funktionstest** – Start/Stop-Buttons

**Einbinden:**
- HA → Einstellungen → Dashboards → + → YAML-Modus → Inhalt einfügen
- Oder als View in ein bestehendes Dashboard kopieren

> **Hinweis**: Die Entity-IDs im Dashboard basieren auf dem Standardnamen.
> Falls HA andere IDs vergibt, unter *Geräte & Dienste → Waveshare Relay*
> die tatsächlichen IDs prüfen und im YAML anpassen.

## Services (Entwicklerwerkzeuge)

| Service                                  | Parameter                                    |
|------------------------------------------|----------------------------------------------|
| `waveshare_relay.funktionstest_start`    | `laufzeit_s`, `pause_s`, `einmalig`          |
| `waveshare_relay.funktionstest_stop`     | –                                            |
| `waveshare_relay.statistik_zuruecksetzen`| –                                            |
| `waveshare_relay.alle_aus`               | –                                            |

## Wichtige Hinweise

- **Nur 1 TCP-Session**: Das Board erlaubt typischerweise nur eine gleichzeitige
  Modbus-TCP-Verbindung. Parallel laufende Modbus-Adapter oder Tools stören sich gegenseitig.
- **Dauer-Tracking**: Einschalt-/Ausschaltdauer wird session-basiert gezählt (ab HA-Start
  bzw. letztem Statistik-Reset). Kein persistentes Speichern über Neustarts hinweg.
- **pymodbus**: Wird automatisch in Version `3.13.0` installiert. Falls Probleme auftreten,
  manuell prüfen: `pip list | grep pymodbus`

## Feature-Übersicht vs. ioBroker-Script

| Feature                     | ioBroker ✓ | HA ✓ |
|-----------------------------|------------|------|
| 8× Relais Switch            | ✓          | ✓    |
| Live-Status (FC01 Poll)     | ✓          | ✓    |
| Schalten (FC05)             | ✓          | ✓    |
| Globale Fehler-/Erfolgszähler| ✓         | ✓    |
| Reaktionszeit               | ✓          | ✓    |
| Pro-Kanal EIN/AUS-Zähler    | ✓          | ✓    |
| Pro-Kanal Einschaltdauer    | —          | ✓    |
| Pro-Kanal Ausschaltdauer    | —          | ✓    |
| Verbindungsprüfung          | (implizit) | ✓    |
| Funktionstest (One-Hot)     | ✓          | ✓    |
| UI-Konfiguration            | —          | ✓    |
| Lovelace Dashboard          | —          | ✓    |
