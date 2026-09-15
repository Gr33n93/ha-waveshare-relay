# Waveshare Modbus PoE Ethernet Relay

[🇩🇪 Deutsch](README.de.md) | [🇬🇧 English](README.md)

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
| `switch` | Relaisanzahl | Ein Schalter pro Relais (Modus: Switch oder Pulse) |
| `select` | Relaisanzahl | Mode-Auswahl (Switch/Pulse), in der Steuerung direkt beim Kanal |
| `binary_sensor` | 1 | Verbindungsstatus |
| `sensor` | 12 + 5 pro Relais | Statistik, Laufzeiten, Zähler und Teststatus |
| `button` | 4 | Funktionstest, Alle aus, Statistik zurücksetzen |

## Modus pro Kanal (Switch / Pulse)

Jeder Kanal ist über die Integrationsoptionen (**Geräte & Dienste → Waveshare
Relay → Konfigurieren**) oder direkt per Mode-Select einzeln konfigurierbar:
Anzeigename, Modus und Impulsdauer.

- **Switch**: normales Ein-/Ausschalten, die Entity zeigt den echten
  Boardzustand.
- **Pulse**: Das Einschalten löst den nativen Waveshare-Impulsbefehl
  aus (Modbus FC05 an Adresse `0x0200 + Kanal`, Zeit in 100-ms-Schritten). Das
  Board schaltet nach der eingestellten Dauer selbstständig zurück – auch
  wenn Home Assistant in der Zwischenzeit nicht erreichbar ist. Gedacht für
  bistabile Relais bzw. Stromstoßschalter. Der Ausschalter beendet einen
  laufenden Impuls sicher.

Der Moduswechsel ändert weder Name noch Entity-ID noch Unique-ID –
Dashboards und Automationen bleiben beim Umschalten unverändert. Zusätzliche
Attribute (`betriebsart` mit `switch`/`pulse`, `impulsdauer_ms`,
`letzter_impuls`) zeigen die aktuelle Konfiguration.

### Mode direkt am Gerät / Dashboard

Zusätzlich zum OptionsDialog gibt es pro Kanal eine Select-Entity
(`select.*_mode`, angezeigt als „Relais N Mode“), mit der sich Switch/Pulse
direkt umstellen lässt – auf der Geräteseite in der **Steuerung** direkt beim
jeweiligen Kanal oder als Karte im Dashboard (Beispiel in
`lovelace_dashboard.yaml`). Eine Umstellung über die Select-Entity wirkt
identisch zum OptionsDialog: sie wird gespeichert und überlebt Neustarts.

## Services

| Service | Beschreibung |
| --- | --- |
| `waveshare_relay.alle_aus` | Schaltet alle Relais aus |
| `waveshare_relay.funktionstest_start` | Startet einen Kanal-Funktionstest |
| `waveshare_relay.funktionstest_stop` | Stoppt den Funktionstest |
| `waveshare_relay.statistik_zuruecksetzen` | Setzt Statistikwerte zurück |

Alle Services akzeptieren optional ein **Zielgerät** (Geräteselector). Ohne
Auswahl wirken sie auf alle konfigurierten Boards – bestehende Automationen
verhalten sich weiterhin wie bisher.

Parameter für `funktionstest_start`:

| Parameter | Standard | Beschreibung |
| --- | ---: | --- |
| `laufzeit_s` | `5` | Einschaltdauer pro Kanal |
| `pause_s` | `0.25` | Pause zwischen Kanälen |
| `einmalig` | `true` | Ein Durchlauf oder Dauertest |
| `device_id` | – | Optional: Board, auf dem der Test läuft |

Während eines Funktionstests sind manuelle Schaltbefehle gesperrt, damit sie
sich nicht mit dem Testablauf überlagern. `alle_aus` bleibt als
Sicherheitsstopp jederzeit verfügbar.

## Verbindungsüberwachung

Fällt das Board aus (Strom- oder Netzwerkverlust), gehen alle Entities des
Geräts auf **Nicht verfügbar** und der Binary-Sensor **„Verbindung"**
(`binary_sensor.*_verbindung`) auf **Aus**. Sobald das Board wieder erreichbar
ist, verbindet sich die Integration automatisch neu – ohne Neustart. Der
letzte Fehler steht in den Diagnose-Sensoren „Letzte Fehlermeldung" und
„Letzter Fehler (Zeit)".

Eine aktive Benachrichtigung richtest du dir selbst per Automation ein.
Beispiel (Benachrichtigung, wenn das Board länger als eine Minute weg ist):

```yaml
automation:
  - alias: "Waveshare Relay Verbindung überwachen"
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
          message: "Das Board ist seit über einer Minute nicht erreichbar."
```

Für eine Handy-Benachrichtigung `notify.persistent_notification` durch
`notify.mobile_app_<gerät>` ersetzen. Die tatsächliche Entity-ID kann je nach
Gerätename abweichen – unter **Entwicklerwerkzeuge → Zustände** nach
`verbindung` suchen.

Hinweis: Impulskanäle (Modus „Pulse") werden bei einer Wiederherstellung
niemals automatisch erneut ausgelöst; normale Kanäle zeigen nach der
Wiederverbindung den tatsächlichen Boardzustand.

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
- Statistik wird pro Board anhand der MAC dauerhaft gespeichert und übersteht
  Neustarts, Reloads und sogar Löschen/Neu-Anlegen des Boards. Nur der
  Reset-Button nullt die Zähler; das Datum der ersten Verbindung bleibt
  erhalten (Sensor „Erste Verbindung“ – zeigt die Alterung des Boards).
- Die Dauer-Sensoren schreiben sich bei jedem Relais-Wechsel fort; der
  aktuell laufende Wert steht als Attribut `aktuell_s` zur Verfügung.
- RS485/RTU-Boards wie das Modbus RTU Relay 4CH werden nicht unterstützt.
- Die Integration nutzt die Modbus-Bibliothek, die Home Assistant über die
  eingebaute Modbus-Integration bereitstellt.
- Unter [docs/HARDWARE.md](docs/HARDWARE.md) steht die verifizierte Register-Map,
  Identifizierungsdetails und die Board-Web-UI (englisch).

## Entwicklung unterstützen

Wenn dir diese Integration hilft, kannst du meine Arbeit mit einem Kaffee
unterstützen. Dein freiwilliger Beitrag hilft bei Weiterentwicklung, Pflege und
Tests mit echter Hardware.

[☕ Auf Ko-fi unterstützen](https://ko-fi.com/nilsarnold)
