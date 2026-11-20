# Eventi Lago Maggiore 📍

Handy-App mit der Event-Agenda für **Ascona, Locarno, Minusio, Tenero, Orselina und Muralto**.
Öffentlich, gratis, ohne Anmeldung: **https://kipferdp.github.io/eventi-lago-maggiore/**

Seit 20.11.2026 als **React-App** (Vite). Die Daten kommen von der offiziellen Schnittstelle
von **Ticino Turismo** und frischen sich jeden Tag automatisch auf (GitHub Actions).

## Aufbau

| Pfad | Zweck |
|------|-------|
| `app/` | Die React-App (Quellcode in `app/src/`, Bilder/Icons/Manifest in `app/public/`) |
| `app/public/events.json` | Die Events (vom Datensammler erzeugt, von der App beim Start geladen) |
| `scraper.py` | Datensammler: holt Liste + Details (Beschreibung, Zeiten, Preise, Tickets) |
| `bapu_events.json` | Programm des Bagno Pubblico Ascona (fehlt in der Schnittstelle) |
| `extra_events.json` | Eigene Ergänzungen (siehe unten) |
| `.github/workflows/update-events.yml` | Täglich: Daten holen → App bauen → veröffentlichen |

## Funktionen

- Highlights (Top-Events) zuoberst je Ort, danach «Läuft gerade» und eine Liste nach Tagen
- Filter nach Zeitraum (Heute, Wochenende, 7 / 30 Tage) und Kategorie
- Suche über alle Orte, auch in der Beschreibung, mit Tippfehler-Toleranz
- Detailseite mit Beschreibung, Zeiten, Eintritt, Tickets, Website, Karte, Kontakt
- Teilen (eigener Link pro Event, z. B. `#/e/locarno/10074`), Kalender-Datei (.ics), Merkliste (nur auf dem Gerät)

## Eigene Ergänzungen (`extra_events.json`)

- `zusatzorte`: ein Event der Schnittstelle zusätzlich in einem weiteren Ort zeigen
  (Beispiel: Winterland 2026/27 steht in der Quelle nur unter Locarno, findet aber auch in Ascona statt).
- `stichwoerter`: zusätzliche Suchwörter je Event-ID (z. B. «Winterwunderland», «Eisbahn»).
- `highlights`: Event-IDs, die zusätzlich als Highlight gelten.
- `events`: ganz eigene Events, die in der Schnittstelle fehlen. Felder:
  `ort` (ascona, locarno, …), `titel`, `start`/`end` (JJJJ-MM-TT), `von`/`bis` (HH:MM),
  `kat`, `ort_text`, `lat`/`lng`, `beschreibung`, `link`, `quelle_name`.
  Nur mit Quelle eintragen.

## Lokal arbeiten

```bash
python3 scraper.py              # Daten holen -> app/public/events.json
cd app && npm install
npm test                        # Prüfungen der Datums-, Such- und Kalender-Logik
npm run dev                     # Entwicklungsserver
npm run build && npm run preview
```

## Veröffentlichung

GitHub Pages, Quelle = **GitHub Actions** (Workflow oben). Jeder Push auf `main`
baut und veröffentlicht die App; der tägliche Lauf holt zusätzlich neue Daten.

## Datenquellen

1. `https://api.ticino.ch/fileadmin/api/events/?lang=de` (Ticino Turismo, offiziell) plus
   Detailseiten `https://api.ticino.ch/de/tinext/events/<slug>`.
2. `quellen.py` (seit 20.11.2026, täglich): Agenda der Stadt Locarno (`https://www.locarno.ch/it/eventi`),
   `https://www.locarnese.events` (Ente Regionale per lo Sviluppo Locarnese e Vallemaggia, Regionen
   Ascona, Locarno, Minusio, Muralto/Orselina, Verzasca/Piano → nur Tenero) und das Winterland-Programm
   (`https://winterland.swiss/programm/?lang=de`). Doppelte Events werden erkannt (`test_quellen.py`).
   Die App ist nicht kommerziell; bei jedem Event steht die Quelle mit Link.
3. Von Hand: `bapu_events.json`, `extra_events.json`.

Ohne Zusatzquellen: `python3 scraper.py --ohne-quellen`.
