# Eventi Lago Maggiore 📍

Handy-App (PWA) mit der Event-Agenda für **Ascona** und **Locarno**.
Daten kommen von der offiziellen Schnittstelle von **Ticino Turismo** und
frischen sich über GitHub Actions **jeden Tag automatisch** auf.

## Dateien
| Datei | Zweck |
|-------|-------|
| `index.html` | Die App (Tabs Ascona/Locarno, Detailseite) |
| `data.js` | Die Events (vom Scraper erzeugt, von der App geladen) |
| `events.json` | Gleiche Daten als JSON |
| `scraper.py` | Holt die Events von der Ticino-API |
| `manifest.json`, `sw.js`, `*.png` | Macht es zur installierbaren App (PWA, offline) |
| `.github/workflows/update-events.yml` | Tägliche automatische Aktualisierung |

## Events von Hand neu holen
```bash
python3 scraper.py --lang de
```

## Hosting: GitHub Pages
1. Repo auf GitHub liegt z. B. unter `https://github.com/<konto>/eventi-lago-maggiore`.
2. In **Settings → Pages**: Source = „Deploy from a branch", Branch = `main`, Ordner = `/ (root)`.
3. Nach 1–2 Minuten ist die App online unter
   `https://<konto>.github.io/eventi-lago-maggiore/`.
4. Am Handy diese URL öffnen → Teilen → **Zum Home-Bildschirm**.

## Automatik
Der Workflow läuft täglich 04:00 UTC (06:00 CH) und kann unter
**Actions → Events aktualisieren → Run workflow** auch von Hand gestartet werden.

## Datenquelle
`https://api.ticino.ch/fileadmin/api/events/?lang=de` (Ticino Turismo, offiziell).
