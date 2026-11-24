# Waveshare Modbus PoE Ethernet Relay

[🇩🇪 Deutsch](README.de.md) | [🇬🇧 English](README.md)

[![Im Home Assistant Marketplace öffnen](https://img.shields.io/badge/Home%20Assistant-Marketplace-41BDF5?style=for-the-badge)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration)
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

## Installation über den Marketplace

Ab Home Assistant **2026.11** ist der Marketplace bereits enthalten. Eine separate
HACS-Installation ist nicht nötig.

1. Öffne als Administrator **Einstellungen → Marketplace**. Bestätige vor der
   ersten Installation den Risikohinweis für Community-Projekte.
2. Suche nach **Waveshare Modbus PoE Ethernet Relay** und öffne den Eintrag.
   Alternativ: [direkt zum Eintrag](https://my.home-assistant.io/redirect/hacs_repository/?owner=Gr33n93&repository=ha-waveshare-relay&category=integration).
3. Wähle **Installieren** und bestätige die angezeigte Version.
4. Fahre mit der [Einrichtung](#einrichtung) fort. Starte Home Assistant nur
   neu, wenn der Marketplace dazu auffordert.

**Home Assistant 2026.10 und älter:** Richte zuerst [HACS](https://www.hacs.xyz/docs/use/)
ein, falls noch nicht geschehen. Öffne **HACS** in der Seitenleiste, suche nach
**Waveshare Modbus PoE Ethernet Relay** und lade die Integration herunter. Starte
Home Assistant anschließend neu und füge die Integration wie unten beschrieben hinzu.

## Einrichtung

Gib im Einrichtungsdialog die Verbindungsdaten des Boards ein. Falls der Dialog
nicht automatisch erscheint, öffne **Einstellungen → Geräte & Dienste →
Integration hinzufügen** und suche nach **Waveshare Modbus PoE Ethernet Relay**.

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

Der Funktionstest-Sensor liefert jetzt die Rohzustände `idle` und `running`,
die in der Oberfläche übersetzt werden. Automationen mit den bisherigen deutschen
Zustandstexten müssen angepasst werden; das Attribut `aktueller_kanal` enthält
den aktuellen Kanal.

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

Beim Laden der Integration wird ein Modbus-Telegramm mit einer bekannten
Impulsdauer erzeugt und geprüft, **ohne etwas an das Board zu senden**.
Schlägt die Prüfung fehl, meldet Home Assistant beim Einschalten eines
Impulskanals **„Impuls nicht gesendet“**. Es wird kein Ersatzbefehl gesendet.
Kanäle im Modus **Switch**, das Ausschalten einzelner Relais und **Alle Relais
aus** bleiben nutzbar. Nach einem Bibliotheksupdate wird beim nächsten Laden
erneut geprüft.

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

Nach erfolgreicher Einrichtung meldet der Sensor **Verbindung** `off`, wenn
eine Abfrage des Boards fehlschlägt. Die Relais und die übrigen Entitäten
werden **nicht verfügbar**. Sobald eine Abfrage wieder gelingt, meldet der
Sensor `on` und die Integration liest die Relaiszustände neu ein. Ein Neustart
ist nicht nötig. Unter **Letzte Fehlermeldung** und **Letzter Fehler (Zeit)**
findest du nach der Wiederverbindung die Details; technische Fehlertexte können
auch bei deutscher Oberfläche auf Englisch erscheinen.

Den Verbindungssensor und seine Entitäts-ID findest du unter
**Einstellungen → Geräte & Dienste → Waveshare Modbus PoE Ethernet Relay**.
Wähle dein Gerät und öffne unter **Diagnose** den Sensor **Verbindung**.
Kopiere seine Entitäts-ID aus den Sensoreinstellungen.

Die folgende Automation benachrichtigt dich, wenn das Board eine Minute lang
nicht erreichbar ist. Ersetze die Beispiel-ID durch die kopierte Entitäts-ID:

```yaml
automation:
  - alias: "Waveshare Relay Verbindung überwachen"
    mode: single
    trigger:
      - platform: state
        entity_id: binary_sensor.dein_verbindungssensor
        to: "off"
        for: "00:01:00"
    action:
      - service: persistent_notification.create
        data:
          title: "Waveshare Relay offline"
          message: "Das Board ist seit über einer Minute nicht erreichbar."
```

Für eine Benachrichtigung auf dem Handy ersetze `persistent_notification.create`
durch die Aktion `notify.mobile_app_<gerät>` deines Handys.

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
