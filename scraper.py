#!/usr/bin/env python3
"""
Event-Scraper fuer die App "Eventi Lago Maggiore".
Holt die Events von der offiziellen Ticino-Turismo-Schnittstelle,
filtert Ascona + Locarno und schreibt sie als data.js (von der App geladen)
sowie events.json (fuer Hosting/Weiterverwendung).

Quelle:  https://api.ticino.ch/fileadmin/api/events/?lang=<lang>
Aufruf:  python3 scraper.py            (Sprache de)
         python3 scraper.py --lang it
"""
import requests, json, argparse, sys
from datetime import datetime, date

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Zurich")
except Exception:
    TZ = None

API = "https://api.ticino.ch/fileadmin/api/events/?lang={lang}"
CITIES = {"Ascona": "ascona", "Locarno": "locarno"}
HEADERS = {"User-Agent": "Mozilla/5.0 (EventiLagoMaggiore/1.0)"}

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Ticino-Kategorie  ->  (App-Key, Anzeige-Label)
CAT_MAP = {
    "musicals":           ("musik",      "Musik"),
    "open-air-festival":  ("festival",   "Festival"),
    "cultural":           ("kultur",     "Kultur"),
    "traditional":        ("tradition",  "Tradition"),
    "art-exhibitions":    ("ausstellung","Ausstellung"),
    "sports":             ("sport",      "Sport"),
    "food-and-wine":      ("kulinarik",  "Kulinarik"),
    "walks-food-and-wine":("kulinarik",  "Kulinarik"),
    "guided-tours":       ("fuehrung",   "Führung"),
    "nature":             ("natur",      "Natur"),
    "markets":            ("markt",      "Markt"),
}
DEFAULT_CAT = ("event", "Event")

# Hauptorte (Wunsch Michael): Seepromenade, Lido, Piazza – pro Stadt.
# Reihenfolge = Priorität. Matching case-insensitive gegen Strasse + Titel + place.
VENUES = {
    "Ascona": [
        ("Seepromenade", ["lungolago"]),
        ("Piazza",       ["piazza giuseppe motta", "piazza g. motta", "piazza motta",
                          "piazza/borgo", "borgo ascona", "borgo di ascona", "borgo"]),
        ("Lido",         ["lido"]),
    ],
    "Locarno": [
        ("Piazza",       ["piazza grande"]),
        ("Seepromenade", ["lungolago"]),
        ("Lido",         ["lido", "respini"]),
    ],
}


def key_venue(city, *texts):
    hay = " ".join(t for t in texts if t).lower()
    for label, words in VENUES.get(city, []):
        if any(w in hay for w in words):
            return label
    return ""


def to_local_date(ms):
    if ms is None:
        return None
    ts = ms / 1000
    if TZ:
        return datetime.fromtimestamp(ts, TZ).date()
    return datetime.utcfromtimestamp(ts).date()


def fmt_date(d):
    return f"{WEEKDAYS[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def date_text(d_from, d_until):
    if not d_from:
        return ""
    if d_until and d_until != d_from:
        return f"{WEEKDAYS[d_from.weekday()]}, {d_from.strftime('%d.%m.')}–{d_until.strftime('%d.%m.%Y')}"
    return fmt_date(d_from)


DAY_MS = 86400000


def assign_parents(lst):
    """Markiert Einzel-Events, die zu einem mehrtägigen Über-Event (Festival)
    am selben Ort und im selben Zeitraum gehören (z. B. Konzerte → Moon+Stars)."""
    umbrellas = [u for u in lst
                 if u.get("isTop") and u["_street"] and (u["_end"] - u["_start"]) >= 2 * DAY_MS]
    for e in lst:
        espan = e["_end"] - e["_start"]
        best = None
        for u in umbrellas:
            if u is e or not u["_street"] or u["_street"] != e["_street"]:
                continue
            uspan = u["_end"] - u["_start"]
            if espan >= uspan:                       # nur kürzere Events sind "Kinder"
                continue
            if u["title"] == e["title"]:
                continue
            if u["_start"] <= e["_start"] <= u["_end"]:
                if best is None or (best["_end"] - best["_start"]) > uspan:
                    best = u                         # spezifischstes (kürzestes) Über-Event
        if best:
            e["parent"] = best["title"]


def category(ev):
    facets = ev.get("listFacetIdAttributeEvent") or []
    for f in facets:
        key = f.replace("events-event-cat-", "")
        if key in CAT_MAP:
            return CAT_MAP[key]
    return DEFAULT_CAT


def build(lang="de"):
    url = API.format(lang=lang)
    print(f"-> hole {url}", file=sys.stderr)
    raw = requests.get(url, headers=HEADERS, timeout=60).json()
    items = [x[0] for x in raw["content"][0]["data"]["items"]]
    print(f"-> {len(items)} Events total", file=sys.stderr)

    today = date.today()
    out = {"ascona": [], "locarno": []}
    seen = set()

    for ev in items:
        city = ev.get("city")
        if city not in CITIES:
            continue
        d_from = to_local_date(ev.get("validFromDate"))
        d_until = to_local_date(ev.get("validUntilDate"))
        end = d_until or d_from
        if end and end < today:        # vergangene Events weglassen
            continue
        key = (ev.get("denomination"), ev.get("validFromDate"))
        if key in seen:                # Duplikate weglassen
            continue
        seen.add(key)

        cat_key, cat_label = category(ev)
        street = (ev.get("street") or "").strip()
        if street:
            loc = f"{street}, {city}"
        else:
            loc = (ev.get("place") or "").strip() or city
        venue = key_venue(city, ev.get("street"), ev.get("denomination"), ev.get("place"))
        # Echte, öffentliche Detailseite auf ascona-locarno.com (nicht die API-Adresse!)
        item_id = ev.get("itemId")
        slug_name = (ev.get("slug") or "").rstrip("/").split("/")[-1]
        link = f"https://www.ascona-locarno.com/de/events/details/{slug_name}/{item_id}" if item_id else ""
        out[CITIES[city]].append({
            "id": str(ev.get("itemId")),
            "cat": cat_key,
            "catLabel": cat_label,
            "title": (ev.get("denomination") or "").strip(),
            "dateText": date_text(d_from, d_until),
            "sortKey": ev.get("validFromDate") or 0,
            "loc": loc or city,
            "venue": venue,           # "" oder Seepromenade/Lido/Piazza
            "keyVenue": bool(venue),  # Hauptort ja/nein
            "image": ev.get("imageName") or "",
            "link": link,
            "lat": ev.get("mapLatitude"),
            "lng": ev.get("mapLongitude"),
            "isTop": bool(ev.get("isTopEvent")),
            "parent": "",
            "_start": ev.get("validFromDate") or 0,
            "_end": ev.get("validUntilDate") or ev.get("validFromDate") or 0,
            "_street": (ev.get("street") or "").strip().lower(),
        })

    for c in out:
        assign_parents(out[c])
        for e in out[c]:
            e.pop("_start", None); e.pop("_end", None); e.pop("_street", None)
        out[c].sort(key=lambda e: e["sortKey"])
    print(f"-> Ascona {len(out['ascona'])}, Locarno {len(out['locarno'])}", file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="de")
    args = ap.parse_args()
    data = build(args.lang)
    stamp = datetime.now(TZ).strftime("%d.%m.%Y %H:%M") if TZ else datetime.now().strftime("%d.%m.%Y %H:%M")
    payload = {"updated": stamp, "events": data}

    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    with open("data.js", "w", encoding="utf-8") as f:
        f.write("// Automatisch erzeugt von scraper.py – nicht von Hand bearbeiten\n")
        f.write("window.EVENT_DATA = ")
        json.dump(payload, f, ensure_ascii=False)
        f.write(";\n")
    print(f"OK – data.js & events.json geschrieben (Stand {stamp})", file=sys.stderr)


if __name__ == "__main__":
    main()
