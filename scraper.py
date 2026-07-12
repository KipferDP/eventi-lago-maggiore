#!/usr/bin/env python3
"""
Event-Scraper fuer die App "Eventi Lago Maggiore".
Holt die Events von der offiziellen Ticino-Turismo-Schnittstelle,
filtert Ascona + Locarno + Minusio + Tenero und schreibt sie als data.js
(von der App geladen) sowie events.json (fuer Hosting/Weiterverwendung).

Quelle:  https://api.ticino.ch/fileadmin/api/events/?lang=<lang>
Aufruf:  python3 scraper.py            (Sprache de)
         python3 scraper.py --lang it
"""
import requests, json, argparse, sys
from datetime import datetime, date, timedelta

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Zurich")
except Exception:
    TZ = None

API = "https://api.ticino.ch/fileadmin/api/events/?lang={lang}"
CITIES = {"Ascona": "ascona", "Locarno": "locarno", "Minusio": "minusio",
          "Tenero": "tenero", "Orselina": "orselina", "Muralto": "muralto"}
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
    "Minusio": [
        ("Seepromenade", ["lungolago", "via alla riva", "rivapiana"]),
        ("Lido",         ["lido"]),
    ],
    "Tenero": [
        ("Seepromenade", ["lungolago"]),
        ("Lido",         ["lido"]),
    ],
    "Orselina": [
        ("Park",   ["parco di orselina", "parco", "via caselle"]),
        ("Cardada",["cardada"]),
        ("Sasso",  ["madonna del sasso", "santuario"]),
    ],
    "Muralto": [
        ("Seepromenade", ["lungolago", "viale verbano", "burbaglio"]),
        ("Lido",         ["lido"]),
        ("Bahnhof",      ["piazza stazione"]),
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


# ---------------------------------------------------------------------------
# Bagno Pubblico Ascona (BaPu) – eigene Events, die die Ticino-API NICHT liefert.
# Quelle: bapu_events.json (von Hand gepflegt). Wird in Ascona eingemischt.
# ---------------------------------------------------------------------------
BAPU_FILE = "bapu_events.json"
BAPU_LABELS = {
    "musik": "Musik", "sport": "Sport", "kulinarik": "Kulinarik", "kino": "Kino",
    "wellness": "Wellness", "kinder": "Kinder", "kurs": "Kurs",
    "festival": "Festival", "kultur": "Kultur", "event": "Event",
}
WD_INDEX = {"Mo": 0, "Di": 1, "Mi": 2, "Do": 3, "Fr": 4, "Sa": 5, "So": 6}


def _parse_iso(s):
    return date(*map(int, s.split("-")))


def _to_ms(d):
    if TZ:
        dt = datetime(d.year, d.month, d.day, tzinfo=TZ)
    else:
        dt = datetime(d.year, d.month, d.day)
    return int(dt.timestamp() * 1000)


def _next_occurrence(day_idxs, start, until):
    """Naechstes Vorkommen ab 'start' (heute) an einem der Wochentage, spaetestens 'until'."""
    horizon = (until - start).days if until else 13
    for i in range(0, max(horizon, 0) + 1):
        d = start + timedelta(days=i)
        if d.weekday() in day_idxs:
            return d
    return start


def add_bapu(out):
    try:
        with open(BAPU_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print("-> BaPu: keine bapu_events.json gefunden, uebersprungen", file=sys.stderr)
        return
    except Exception as e:
        print(f"-> BaPu uebersprungen (Fehler: {e})", file=sys.stderr)
        return

    v = cfg.get("venue", {})
    city = v.get("city", "Ascona")
    loc = ", ".join(x for x in [v.get("street"), city] if x) or city
    lat, lng = v.get("lat"), v.get("lng")
    link = v.get("link", "")
    today = date.today()
    added = 0
    n = 0

    def emit(cat, title, note, sortkey_date, datetext):
        nonlocal added, n
        label = BAPU_LABELS.get(cat, cat.capitalize())
        full = title if not note else f"{title} – {note}"
        out.setdefault(CITIES[city], out.get("ascona", []))
        out[CITIES[city]].append({
            "id": f"bapu-{n}",
            "cat": cat,
            "catLabel": label,
            "title": full,
            "dateText": datetext,
            "sortKey": _to_ms(sortkey_date),
            "loc": loc,
            "venue": "",
            "keyVenue": False,
            "image": "",
            "link": link,
            "lat": lat,
            "lng": lng,
            "isTop": False,
            "parent": "",
        })
        n += 1
        added += 1

    # Einzel-Events (nur noch kommende, wie die API-Logik)
    for e in cfg.get("single", []):
        try:
            d = _parse_iso(e["date"])
        except Exception:
            continue
        if d < today:
            continue
        time = (e.get("time") or "").strip()
        if e.get("dateOverride"):
            dt = e["dateOverride"]
        else:
            dt = fmt_date(d) + (f" · {time}" if time else "")
        emit(e.get("cat", "event"), e["title"], e.get("note", ""), d, dt)

    # Wiederkehrende Angebote (eine Karte je Serie, solange noch aktiv)
    for r in cfg.get("recurring", []):
        until = _parse_iso(r["until"]) if r.get("until") else None
        if until and until < today:
            continue
        days = [WD_INDEX[x] for x in r.get("days", []) if x in WD_INDEX]
        sk = _next_occurrence(days, today, until) if days else today
        day_txt = "/".join(r.get("days", [])) if r.get("days") else "woechentlich"
        time = (r.get("time") or "").strip()
        parts = [f"jeden {day_txt}" if r.get("days") else "woechentlich"]
        if time:
            parts.append(time)
        if until:
            parts.append(f"bis {until.strftime('%d.%m.')}")
        emit(r.get("cat", "event"), r["title"], r.get("note", ""), sk, " · ".join(parts))

    print(f"-> BaPu: {added} Events in {city} eingemischt", file=sys.stderr)


def build(lang="de"):
    url = API.format(lang=lang)
    print(f"-> hole {url}", file=sys.stderr)
    raw = requests.get(url, headers=HEADERS, timeout=60).json()
    items = [x[0] for x in raw["content"][0]["data"]["items"]]
    print(f"-> {len(items)} Events total", file=sys.stderr)

    today = date.today()
    out = {slug: [] for slug in CITIES.values()}
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
    # BaPu-Events (nicht in der Ticino-API) einmischen und Ascona neu sortieren
    add_bapu(out)
    out["ascona"].sort(key=lambda e: e["sortKey"])
    summary = ", ".join(f"{name} {len(out[slug])}" for name, slug in CITIES.items())
    print(f"-> {summary}", file=sys.stderr)
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
