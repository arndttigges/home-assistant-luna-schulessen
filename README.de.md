# Luna Schulessen für Home Assistant

[English documentation](README.md)

![Logo von Luna Schulessen](custom_components/luna_schulessen/brand/icon.png)

Diese benutzerdefinierte Home-Assistant-Integration zeigt bestätigte Schulessen-Bestellungen aus dem [Luna-Elternportal](https://bestellen.luna.de/). Sie liest den aktuellen und den nächsten Monat beim Start und danach alle zwei Stunden. Die Integration ist ein unabhängiges Projekt.

## Voraussetzungen

- Getestet mit Home Assistant Core 2026.11.1.
- Ein Luna-Elternkonto mit genau einem Schulessen-Vertrag.
- Home Assistant muss `bestellen.luna.de` per HTTPS erreichen können.

## Installation

### Marketplace (ab Home Assistant 2026.11)

[![Luna Schulessen in Home Assistant öffnen](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=arndttigges&repository=home-assistant-luna-schulessen&category=integration)

1. Nutze den Link oben oder öffne **Einstellungen → Marketplace → Über Link hinzufügen** und füge `https://github.com/arndttigges/home-assistant-luna-schulessen` ein.
2. Verbinde GitHub, falls du dazu aufgefordert wirst, und bestätige das Hinzufügen. Wähle **Integration**, falls Home Assistant nach dem Typ fragt.
3. Öffne **Luna Schulessen** und wähle **Installieren**. Starte Home Assistant neu, falls du dazu aufgefordert wirst.

### Klassisches HACS (vor Home Assistant 2026.11)

1. Öffne **HACS → ⋮ → Benutzerdefinierte Repositorys**.
2. Füge `https://github.com/arndttigges/home-assistant-luna-schulessen` ein, wähle **Integration** und füge das Repository hinzu.
3. Öffne **Luna Schulessen** in HACS, wähle **Herunterladen** und starte Home Assistant neu.

### Manuelle Installation

1. Lade das Repository über **Code → Download ZIP** herunter und entpacke es.
2. Kopiere den ganzen Ordner `custom_components/luna_schulessen` in das Home-Assistant-Konfigurationsverzeichnis. Auf Home Assistant OS ist der Zielpfad `/config/custom_components/luna_schulessen`.
3. Starte Home Assistant Core neu.

Jeder erfolgreiche [GitHub-Actions-Build](https://github.com/arndttigges/home-assistant-luna-schulessen/actions/workflows/build.yml) stellt unter **Artifacts** auch `luna_schulessen.zip` bereit. Darin liegt der Ordner `custom_components/luna_schulessen` für die manuelle Installation.

### Integration einrichten

1. Öffne **Einstellungen → Geräte & Dienste → Integration hinzufügen** und wähle **Luna Schulessen**. Der Marketplace kann die Einrichtung auch direkt nach der Installation öffnen.
2. Gib deinen Luna-Benutzernamen oder deine E-Mail-Adresse und dein Luna-Passwort ein. Home Assistant speichert die Zugangsdaten im Integrationseintrag und verwendet sie für die Anmeldung per HTTPS am Luna-Portal.

![Luna Schulessen in der Suche „Integration hinzufügen“](docs/screenshots/add-integration.jpg)

![Installiertes Luna-Icon in Home Assistant](docs/screenshots/installed-icon.jpg)

## Entitäten

Die IDs sind die Vorschläge von Home Assistant. Deine Instanz kann bei einem Namenskonflikt ein Suffix vergeben.

| Entität | Bedeutung |
| --- | --- |
| `calendar.luna_schulessen` | Bestätigte Bestellungen als ganztägige Termine. Änderungen erscheinen nach dem nächsten erfolgreichen Abruf. |
| `binary_sensor.luna_schulessen_nachster_monat_buchbar` | `on`, sobald Luna für mindestens einen Tag im nächsten Monat ein Menü zur Auswahl freigibt. |
| `sensor.luna_schulessen_nachster_tag_ohne_auswahl` | Datum des ersten künftigen Tags ohne Auswahl, für den Luna ein buchbares Menü oder einen Schließhinweis anzeigt. |

Der Binärsensor enthält `monat` im Format `JJJJ-MM`, `buchbare_tage` und `tage_ohne_auswahl`. Die letzte Zahl zählt nur buchbare Tage ohne bestätigte Bestellung.

Der Datumssensor enthält `buchbar`, `ferien`, `luna_hinweis` sowie `naechster_buchbarer_tag_ohne_auswahl`. `luna_hinweis` übernimmt Lunas Bezeichnung, zum Beispiel „Weihnachtsferien“. Das zusätzliche Datumsattribut ist leer, wenn in den abgefragten Monaten kein künftiger buchbarer Tag ohne Auswahl liegt.

## Beispiel für eine Wochenliste

Diese Karte zeigt im Dashboard die Bestellungen der nächsten sieben Tage.

```yaml
type: calendar
title: Bestelltes Schulessen
initial_view: listWeek
entities:
  - calendar.luna_schulessen
```

Für eine Erinnerung bei Freischaltung des nächsten Monats kannst du den Wechsel des Binärsensors auf `on` als Auslöser und `tage_ohne_auswahl > 0` als Bedingung verwenden. Für eine Erinnerung vor dem nächsten offenen Essen eignet sich `naechster_buchbarer_tag_ohne_auswahl`, weil es Schließtage ohne buchbares Menü überspringt.

## Fehlerbehebung

- **Anmeldung abgelehnt** – Prüfe die Zugangsdaten und teste sie im Luna-Elternportal. Bei geändertem Passwort bietet Home Assistant eine erneute Anmeldung an.
- **Bestellübersicht konnte nicht gelesen werden** – Prüfe, ob das Elternportal genau einen Schulessen-Vertrag enthält und Home Assistant das Portal erreichen kann.
- **Sensoren sind nicht verfügbar** – Prüfe im Home-Assistant-Protokoll Meldungen zur Integration `luna_schulessen`. Kalender und Auswahlstatus verwenden unterschiedliche Ansichten des Luna-Portals. Eine Änderung am Portal kann eine Anpassung der Integration erforderlich machen.

## Lizenz

Luna Schulessen steht unter der GNU General Public License, Version 3 (`GPL-3.0-only`). Den vollständigen Text findest du in [LICENSE](LICENSE).
