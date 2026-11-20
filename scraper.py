#!/usr/bin/env python3
"""
Datensammler für die App «Eventi Lago Maggiore» (React-Version, Datenformat 2).

Holt die Events von der offiziellen Schnittstelle von Ticino Turismo,
behält nur die App-Orte, lädt pro Event die Detailseite (Beschreibung,
Uhrzeiten, Preise, Tickets, Kontakt) und schreibt app/public/events.json.

Eigene Ergänzungen (von Hand gepflegt, siehe README):
- bapu_events.json  : Programm des Bagno Pubblico Ascona (fehlt in der API)
- extra_events.json : Event zusätzlich an weiteren Orten zeigen (z. B.
                      Winterland auch in Ascona), Suchwörter, eigene Events

Aufruf:  python3 scraper.py                     (Deutsch, mit Details)
         python3 scraper.py --no-details        (schneller Test ohne Details)
         python3 scraper.py --out pfad/events.json
"""
import argparse
import html
import json
import os
import re
import sys
import time
from datetime import date, datetime, timedelta

import requests

try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Europe/Zurich")
except Exception:  # pragma: no cover
    TZ = None

API = "https://api.ticino.ch/fileadmin/api/events/?lang={lang}"
HEADERS = {"User-Agent": "Mozilla/5.0 (EventiLagoMaggiore/2.0; +https://kipferdp.github.io/eventi-lago-maggiore/)"}
DEFAULT_OUT = "app/public/events.json"
DETAIL_PAUSE = 0.25          # Sekunden zwischen Detail-Abfragen (Server schonen)
MIN_EVENTS = 20              # weniger = Störung der Quelle, alte Daten behalten

# API-Ort -> App-Schlüssel (Reihenfolge = Tabs in der App)
CITIES = {"Ascona": "ascona", "Locarno": "locarno", "Minusio": "minusio",
          "Tenero": "tenero", "Orselina": "orselina", "Muralto": "muralto"}
CITY_NAME = {v: k for k, v in CITIES.items()}

WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

# Ticino-Kategorie -> (App-Key, Anzeige)
CAT_MAP = {
    "musicals":            ("musik",       "Musik"),
    "open-air-festival":   ("festival",    "Festival"),
    "cultural":            ("kultur",      "Kultur"),
    "traditional":         ("tradition",   "Tradition"),
    "art-exhibitions":     ("ausstellung", "Ausstellung"),
    "sports":              ("sport",       "Sport"),
    "food-and-wine":       ("kulinarik",   "Kulinarik"),
    "walks-food-and-wine": ("kulinarik",   "Kulinarik"),
    "guided-tours":        ("fuehrung",    "Führung"),
    "nature":              ("natur",       "Natur"),
    "markets":             ("markt",       "Markt"),
}
# Feste haben Vorrang als Haupt-Kategorie (Winterland = Weihnachten, nicht Musik)
FEST_MAP = {
    "festivities-christmas":        ("weihnachten", "Weihnachten"),
    "festivities-new-years":        ("silvester",   "Silvester & Neujahr"),
    "festivities-carnival":         ("fasnacht",    "Fasnacht"),
    "festivities-national-holiday": ("august1",     "1. August"),
}
DEFAULT_CAT = ("event", "Event")
LABELS = {k: v for k, v in list(CAT_MAP.values()) + list(FEST_MAP.values())}
LABELS.update({"kino": "Kino", "wellness": "Wellness", "kinder": "Kinder",
               "kurs": "Kurs", "event": "Event"})

# Zusätzliche Suchwörter je Facette (damit z. B. «Advent» Weihnachts-Events findet)
FACET_WORDS = {
    "festivities-christmas": "Weihnachten Advent Christmas Natale Noël Weihnachtsmarkt",
    "festivities-new-years": "Silvester Neujahr Capodanno New Year",
    "festivities-carnival": "Fasnacht Fasching Karneval Carnevale",
    "festivities-national-holiday": "Nationalfeiertag 1. August",
    "seasons-winter": "Winter",
    "seasons-spring": "Frühling",
    "seasons-summer": "Sommer",
    "seasons-autumn": "Herbst",
}

DAY_MS = 86400000


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def today_local():
    return datetime.now(TZ).date() if TZ else date.today()


def to_local_date(ms):
    if ms is None:
        return None
    ts = ms / 1000
    return datetime.fromtimestamp(ts, TZ).date() if TZ else datetime.utcfromtimestamp(ts).date()


def parse_iso(s):
    try:
        return date(*map(int, s.split("-")))
    except Exception:
        return None


def to_ms(d):
    dt = datetime(d.year, d.month, d.day, tzinfo=TZ) if TZ else datetime(d.year, d.month, d.day)
    return int(dt.timestamp() * 1000)


def fmt_day(d, year=True):
    return f"{WEEKDAYS[d.weekday()]}, {d.strftime('%d.%m.%Y' if year else '%d.%m.')}"


def date_text(d_from, d_until):
    if not d_from:
        return ""
    if d_until and d_until != d_from:
        return f"{fmt_day(d_from, year=d_from.year != d_until.year)} – {fmt_day(d_until)}"
    return fmt_day(d_from)


def time_text(t_from, t_to):
    t_from, t_to = (t_from or "").strip(), (t_to or "").strip()
    if t_from and t_to and t_to != t_from:
        return f"{t_from}–{t_to} Uhr"
    if t_from:
        return f"{t_from} Uhr"
    return ""


def clean_text(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    return re.sub(r"[ \t ]+", " ", s).strip()


def safe_url(u):
    u = (u or "").strip()
    if u.startswith(("https://", "http://")):
        return u
    return ""


def domain_url(domain):
    d = (domain or "").strip().strip("/")
    if not d:
        return ""
    if d.startswith(("https://", "http://")):
        return d
    if re.fullmatch(r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[^\s]*)?", d):
        return "https://" + d
    return ""


def html_to_paragraphs(h, limit=4000):
    """Beschreibung (HTML) -> Absätze als reiner Text + Links daraus."""
    if not h:
        return [], []
    links = []
    for m in re.finditer(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', h, re.I | re.S):
        url = safe_url(html.unescape(m.group(1)))
        label = clean_text(m.group(2))
        if url and label and all(l["url"] != url for l in links):
            links.append({"label": label, "url": url})
    t = re.sub(r"(?i)<br\s*/?>", "\n", h)
    t = re.sub(r"(?i)</(p|div|li|h[1-6]|ul|ol)>", "\n\n", t)
    t = re.sub(r"(?i)<li[^>]*>", "• ", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    paras = []
    total = 0
    for p in re.split(r"\n\s*\n", t):
        p = "\n".join(re.sub(r"[ \t ]+", " ", line).strip() for line in p.split("\n")).strip()
        if not p:
            continue
        if total + len(p) > limit:
            paras.append(p[: max(0, limit - total)].rstrip() + " …")
            break
        paras.append(p)
        total += len(p)
    return paras, links


def sized_image(url, width):
    url = safe_url(url)
    if not url:
        return ""
    if "cdn.sanity.io" in url:
        base = url.split("?")[0]
        return f"{base}?fm=webp&q=85&w={width}"
    return url


def key_cats(facets_event, facets_all):
    """Haupt-Kategorie + Liste aller Kategorien."""
    cats = []
    fest = [FEST_MAP[f] for f in facets_all if f in FEST_MAP]
    for f in facets_event:
        k = f.replace("events-event-cat-", "")
        if k in CAT_MAP:
            cats.append(CAT_MAP[k])
    ordered = []
    for c in fest + cats:
        if c[0] not in [o[0] for o in ordered]:
            ordered.append(c)
    if not ordered:
        ordered = [DEFAULT_CAT]
    return ordered[0], [c[0] for c in ordered]


def assign_parents(lst):
    """Einzel-Events, die zu einem mehrtägigen Top-Event am selben Ort gehören
    (z. B. Konzerte -> Moon&Stars), bekommen «Teil von»."""
    umbrellas = [u for u in lst
                 if u.get("isTop") and u["_street"] and (u["_end"] - u["_start"]) >= 2 * DAY_MS]
    for e in lst:
        espan = e["_end"] - e["_start"]
        best = None
        for u in umbrellas:
            if u is e or u["_street"] != e["_street"] or u["title"] == e["title"]:
                continue
            uspan = u["_end"] - u["_start"]
            if espan >= uspan:
                continue
            if u["_start"] <= e["_start"] <= u["_end"]:
                if best is None or (best["_end"] - best["_start"]) > uspan:
                    best = u
        if best:
            e["parent"] = best["title"]


# ---------------------------------------------------------------------------
# Details von der Ticino-API
# ---------------------------------------------------------------------------
def fetch_detail(session, url):
    r = session.get(url, headers=HEADERS, timeout=40)
    r.raise_for_status()
    return r.json()["content"][0]["data"]["item"]


def apply_detail(e, it):
    """Felder aus der Detailseite übernehmen (nur was dort steht)."""
    dates = []
    for cd in it.get("cleanDates") or []:
        s, en = parse_iso(cd.get("startDate") or ""), parse_iso(cd.get("endDate") or "")
        if not s:
            continue
        dates.append({"start": s.isoformat(), "end": (en or s).isoformat(),
                      "from": (cd.get("startTime") or "").strip(),
                      "to": (cd.get("endTime") or "").strip()})
    if dates:
        dates.sort(key=lambda x: (x["start"], x["from"]))
        e["dates"] = dates
        if len(dates) == 1:
            e["timeText"] = time_text(dates[0]["from"], dates[0]["to"])
        else:
            e["timeText"] = f"{len(dates)} Termine"

    paras, links = html_to_paragraphs(it.get("description") or "")
    e["desc"] = paras
    if links:
        e["descLinks"] = links
    e["summary"] = clean_text(it.get("summary") or it.get("leadText") or "")
    loc = clean_text(it.get("infoLocation") or "")
    if loc:
        e["loc"] = loc

    prices = []
    for p in it.get("prices") or []:
        if p.get("priceType") == "free":
            prices.append("kostenlos")
            continue
        title = clean_text(p.get("title") or "")
        val = clean_text(p.get("labelPrice") or p.get("value") or "")
        txt = f"{title}: {val}" if title and val else (title or val)
        if txt and txt not in prices:
            prices.append(txt)
    if prices:
        e["prices"] = prices

    for u in it.get("eventUrls") or []:
        url = safe_url(u.get("url"))
        if url:
            platform = (u.get("booking_platform") or "").strip()
            label = "Tickets & Infos" if platform and platform != "external" else "Infos & Tickets beim Veranstalter"
            e["tickets"] = {"url": url, "label": label}
            break

    contact = it.get("infoContact") or it.get("organizerContact") or {}
    web = domain_url(contact.get("domain"))
    if not web:
        web = domain_url((it.get("organizerContact") or {}).get("domain"))
    if web:
        e["website"] = web
    if contact.get("phone"):
        e["phone"] = contact["phone"].strip()
    if contact.get("email"):
        e["email"] = contact["email"].strip()
    org = (it.get("organizerContact") or {}).get("company") or ""
    if org.strip():
        e["organizer"] = org.strip()

    for v in it.get("videos") or []:
        url = safe_url(v.get("publicUrl") or (v.get("properties") or {}).get("originalUrl"))
        if url:
            e["video"] = url
            break

    imgs = it.get("images") or []
    if imgs:
        big = sized_image(imgs[0].get("publicUrl"), 1000)
        if big:
            e["imageLarge"] = big
    if it.get("isCancelled"):
        e["cancelled"] = True
        e["cancelledText"] = clean_text(it.get("cancelledText") or "")
    if it.get("recurringAnnuallyText"):
        e["recurringText"] = clean_text(it["recurringAnnuallyText"])


# ---------------------------------------------------------------------------
# Haupt-Sammlung
# ---------------------------------------------------------------------------
def add_also_in(out):
    """«Auch in»: Events mit gleicher uid in mehreren Orten kennzeichnen."""
    places = {}
    for c, lst in out.items():
        for e in lst:
            places.setdefault(e["uid"], []).append(c)
    for c, lst in out.items():
        for e in lst:
            others = [p for p in places[e["uid"]] if p != c]
            if others:
                e["alsoIn"] = others


def build(lang="de", details=True, sources=True):
    url = API.format(lang=lang)
    print(f"-> hole {url}", file=sys.stderr)
    raw = requests.get(url, headers=HEADERS, timeout=90).json()
    items = [x[0] for x in raw["content"][0]["data"]["items"]]
    print(f"-> {len(items)} Events total in der API", file=sys.stderr)

    today = today_local()
    out = {slug: [] for slug in CITIES.values()}
    seen = set()
    session = requests.Session()
    n_detail_ok = n_detail_err = 0

    for ev in items:
        city = ev.get("city")
        if city not in CITIES:
            continue
        d_from = to_local_date(ev.get("validFromDate"))
        d_until = to_local_date(ev.get("validUntilDate"))
        end = d_until or d_from
        if end and end < today:
            continue
        key = (ev.get("denomination"), ev.get("validFromDate"))
        if key in seen:
            continue
        seen.add(key)

        facets_event = ev.get("listFacetIdAttributeEvent") or []
        facets_all = ev.get("listFacetIdAttribute") or []
        (cat, cat_label), cats = key_cats(facets_event, facets_all)
        street = (ev.get("street") or "").strip()
        loc = f"{street}, {city}" if street else ((ev.get("place") or "").strip() or city)
        item_id = ev.get("itemId")
        slug_name = (ev.get("slug") or "").rstrip("/").split("/")[-1]
        link = f"https://www.ascona-locarno.com/de/events/details/{slug_name}/{item_id}" if item_id else ""
        words = " ".join(FACET_WORDS[f] for f in facets_all if f in FACET_WORDS)

        e = {
            "id": str(item_id),
            "uid": f"ticino-{item_id}",
            "city": CITIES[city],
            "title": (ev.get("denomination") or "").strip(),
            "cat": cat,
            "catLabel": cat_label,
            "cats": cats,
            "start": d_from.isoformat() if d_from else "",
            "end": (d_until or d_from).isoformat() if d_from else "",
            "dateText": date_text(d_from, d_until),
            "timeText": "",
            "sortKey": ev.get("validFromDate") or 0,
            "loc": loc or city,
            "lat": ev.get("mapLatitude"),
            "lng": ev.get("mapLongitude"),
            "image": sized_image(ev.get("imageName"), 600),
            "link": link,
            "isTop": bool(ev.get("isTopEvent")),
            "parent": "",
            "keywords": words,
            "source": "Ticino Turismo",
            "_start": ev.get("validFromDate") or 0,
            "_end": ev.get("validUntilDate") or ev.get("validFromDate") or 0,
            "_street": street.lower(),
        }
        if details and ev.get("slug", "").startswith("https://api.ticino.ch/"):
            try:
                apply_detail(e, fetch_detail(session, ev["slug"]))
                n_detail_ok += 1
            except Exception as ex:  # Details sind ein Plus, kein Muss
                n_detail_err += 1
                print(f"   Details fehlen für {item_id}: {ex}", file=sys.stderr)
            time.sleep(DETAIL_PAUSE)
        out[CITIES[city]].append(e)

    for c in out:
        assign_parents(out[c])
        for e in out[c]:
            for k in ("_start", "_end", "_street"):
                e.pop(k, None)
    if details:
        print(f"-> Details: {n_detail_ok} ok, {n_detail_err} Fehler", file=sys.stderr)

    add_bapu(out, today)
    add_extra(out, today)
    if sources:
        # weitere Agenden (Stadt Locarno, locarnese.events, Winterland); Doppel werden erkannt
        import quellen
        quellen.add_sources(out, today.isoformat(), LABELS)
    add_also_in(out)
    for c in out:
        out[c].sort(key=lambda e: (e.get("start") or "", e.get("title") or ""))
    summary = ", ".join(f"{CITY_NAME[s]} {len(out[s])}" for s in CITIES.values())
    print(f"-> {summary}", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Bagno Pubblico Ascona (BaPu) – eigenes Programm, fehlt in der API
# ---------------------------------------------------------------------------
BAPU_FILE = "bapu_events.json"
WD_INDEX = {"Mo": 0, "Di": 1, "Mi": 2, "Do": 3, "Fr": 4, "Sa": 5, "So": 6}


def _next_occurrence(day_idxs, start, until):
    horizon = (until - start).days if until else 13
    for i in range(0, max(horizon, 0) + 1):
        d = start + timedelta(days=i)
        if d.weekday() in day_idxs:
            return d
    return start


def add_bapu(out, today):
    try:
        with open(BAPU_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print("-> BaPu: keine bapu_events.json, übersprungen", file=sys.stderr)
        return
    except Exception as ex:
        print(f"-> BaPu übersprungen (Fehler: {ex})", file=sys.stderr)
        return

    v = cfg.get("venue", {})
    city_key = CITIES.get(v.get("city", "Ascona"), "ascona")
    loc = ", ".join(x for x in [v.get("name"), v.get("street"), CITY_NAME[city_key]] if x)
    n = 0

    def emit(cat, title, note, d_start, d_end, datetext, timetext, ev_link=None, recurring=""):
        nonlocal n
        full = title if not note else f"{title} – {note}"
        out[city_key].append({
            "id": f"bapu-{n}", "uid": f"bapu-{n}", "city": city_key,
            "title": full, "cat": cat, "catLabel": LABELS.get(cat, cat.capitalize()), "cats": [cat],
            "start": d_start.isoformat(), "end": d_end.isoformat(),
            "dateText": datetext, "timeText": timetext, "sortKey": to_ms(d_start),
            "loc": loc, "lat": v.get("lat"), "lng": v.get("lng"), "image": "",
            "link": safe_url(ev_link) or safe_url(v.get("link")), "isTop": False, "parent": "",
            "keywords": "BaPu Bagno Pubblico Lido Strandbad", "source": "Bagno Pubblico Ascona",
            "recurringText": recurring,
        })
        n += 1

    for e in cfg.get("single", []):
        d = parse_iso(e.get("date", ""))
        if not d or d < today:
            continue
        time_ = (e.get("time") or "").strip()
        dt = e.get("dateOverride") or fmt_day(d)
        emit(e.get("cat", "event"), e["title"], e.get("note", ""), d, d, dt,
             f"ca. {time_} Uhr" if time_ else "", e.get("link"))

    for r in cfg.get("recurring", []):
        until = parse_iso(r["until"]) if r.get("until") else None
        if until and until < today:
            continue
        days = [WD_INDEX[x] for x in r.get("days", []) if x in WD_INDEX]
        nxt = _next_occurrence(days, today, until) if days else today
        day_txt = "jeden " + "/".join(r["days"]) if r.get("days") else "wöchentlich"
        time_ = (r.get("time") or "").strip()
        dt = day_txt + (f" bis {until.strftime('%d.%m.%Y')}" if until else "")
        emit(r.get("cat", "event"), r["title"], r.get("note", ""), nxt, until or nxt, dt,
             f"ca. {time_} Uhr" if time_ else "", r.get("link"), recurring=dt)
    print(f"-> BaPu: {n} Events eingemischt", file=sys.stderr)


# ---------------------------------------------------------------------------
# Eigene Ergänzungen: extra_events.json
# ---------------------------------------------------------------------------
EXTRA_FILE = "extra_events.json"


def add_extra(out, today):
    try:
        with open(EXTRA_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        return
    except Exception as ex:
        print(f"-> Ergänzungen übersprungen (Fehler: {ex})", file=sys.stderr)
        return

    by_id = {}
    for c, lst in out.items():
        for e in lst:
            by_id.setdefault(e["id"], e)

    # 1) Suchwörter
    for ev_id, words in (cfg.get("stichwoerter") or {}).items():
        e = by_id.get(str(ev_id))
        if e:
            e["keywords"] = (e.get("keywords", "") + " " + " ".join(words)).strip()

    # 1b) Hinweise und Preise am Hauptort (der Ort aus der API)
    for ev_id, h in (cfg.get("hinweise") or {}).items():
        e = by_id.get(str(ev_id))
        if not e:
            continue
        if h.get("hinweis"):
            e["note"] = h["hinweis"]
        if h.get("prices"):
            e["prices"] = h["prices"]
        if safe_url(h.get("website")):
            e["website"] = safe_url(h["website"])

    # 2) Highlights (zusätzlich zu den Top-Events der API)
    for ev_id in cfg.get("highlights") or []:
        e = by_id.get(str(ev_id))
        if e:
            e["isTop"] = True

    # 3) Event zusätzlich an weiteren Orten zeigen
    added_places = 0
    for z in cfg.get("zusatzorte") or []:
        base = by_id.get(str(z.get("id")))
        city_key = z.get("ort")
        if not base or city_key not in out:
            continue
        if any(e["uid"] == base["uid"] for e in out[city_key]):
            continue
        copy = json.loads(json.dumps(base))
        copy["city"] = city_key
        copy["parent"] = ""
        for k in ("loc", "lat", "lng"):
            if z.get(k) not in (None, ""):
                copy[k] = z[k]
        if z.get("hinweis"):
            copy["note"] = z["hinweis"]
        # Ortsspezifische Angaben (z. B. andere Daten, Zeiten, Preise als am Hauptort)
        f = z.get("felder") or {}
        d_s, d_e = parse_iso(f.get("start", "")), parse_iso(f.get("end", ""))
        if d_s:
            copy["start"] = d_s.isoformat()
            copy["end"] = (d_e or d_s).isoformat()
            copy["dates"] = [{"start": copy["start"], "end": copy["end"], "from": "", "to": ""}]
            copy["dateText"] = date_text(d_s, d_e if d_e and d_e != d_s else None)
            copy["sortKey"] = to_ms(d_s)
        for k in ("timeText", "prices", "website", "summary"):
            if f.get(k):
                copy[k] = f[k]
        if f.get("tickets"):
            copy["tickets"] = {"url": safe_url(f["tickets"]), "label": "Tickets"}
        out[city_key].append(copy)
        added_places += 1

    # 4) Ganz eigene Events (nicht in der API). Termine entweder als
    #    start/end (+ von/bis) oder als Liste «termine» [{datum, von, bis}].
    added_own = 0
    for i, x in enumerate(cfg.get("events") or []):
        city_key = x.get("ort")
        if city_key not in out or not x.get("titel"):
            continue
        dates = []
        for t in x.get("termine") or []:
            d = parse_iso(t.get("datum", ""))
            if d:
                dates.append({"start": d.isoformat(), "end": d.isoformat(),
                              "from": (t.get("von") or "").strip(), "to": (t.get("bis") or "").strip()})
        if not dates:
            d_s = parse_iso(x.get("start", ""))
            d_e = parse_iso(x.get("end", "")) or d_s
            if not d_s:
                continue
            dates = [{"start": d_s.isoformat(), "end": d_e.isoformat(),
                      "from": (x.get("von") or "").strip(), "to": (x.get("bis") or "").strip()}]
        dates.sort(key=lambda o: (o["start"], o["from"]))
        dates = [o for o in dates if parse_iso(o["end"]) >= today]
        if not dates:
            continue
        d_first, d_last = parse_iso(dates[0]["start"]), parse_iso(max(o["end"] for o in dates))
        cat = x.get("kat", "event")
        cats = [cat] + [c for c in (x.get("kats") or []) if c != cat]
        uid = x.get("id") or f"extra-{i}"
        e = {
            "id": uid, "uid": uid, "city": city_key, "title": x["titel"],
            "cat": cat, "catLabel": LABELS.get(cat, cat.capitalize()), "cats": cats,
            "start": d_first.isoformat(), "end": d_last.isoformat(), "dates": dates,
            "dateText": date_text(d_first, d_last if d_last != d_first else None),
            "timeText": time_text(dates[0]["from"], dates[0]["to"]) if len(dates) == 1 else f"{len(dates)} Termine",
            "sortKey": to_ms(d_first),
            "loc": x.get("ort_text") or CITY_NAME[city_key], "lat": x.get("lat"), "lng": x.get("lng"),
            "image": safe_url(x.get("bild")), "link": safe_url(x.get("link")),
            "isTop": bool(x.get("highlight")), "parent": x.get("teil_von") or "",
            "summary": x.get("kurz") or "",
            "desc": [p for p in (x.get("beschreibung") or "").split("\n\n") if p.strip()],
            "keywords": " ".join(x.get("stichwoerter") or []),
            "source": x.get("quelle_name") or "Eigene Ergänzung",
        }
        if x.get("preise"):
            e["prices"] = x["preise"]
        if safe_url(x.get("website")):
            e["website"] = safe_url(x["website"])
        if safe_url(x.get("tickets")):
            e["tickets"] = {"url": safe_url(x["tickets"]), "label": "Tickets"}
        out[city_key].append(e)
        added_own += 1
    print(f"-> Ergänzungen: {added_places} Zusatzorte, {added_own} eigene Events", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="de")
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--no-details", action="store_true")
    ap.add_argument("--ohne-quellen", action="store_true", help="nur Ticino-Schnittstelle + eigene Ergänzungen")
    args = ap.parse_args()
    data = build(args.lang, details=not args.no_details, sources=not args.ohne_quellen)
    total = sum(len(v) for v in data.values())
    if total < MIN_EVENTS:
        # Schutz: liefert die API einmal (fast) nichts, bleiben die alten Daten stehen
        print(f"FEHLER – nur {total} Events erhalten (Minimum {MIN_EVENTS}), alte Datei bleibt unverändert", file=sys.stderr)
        sys.exit(1)
    now = datetime.now(TZ) if TZ else datetime.now()
    payload = {
        "version": 2,
        "updated": now.strftime("%d.%m.%Y %H:%M"),
        "updatedIso": now.isoformat(timespec="minutes"),
        "source": "Ticino Turismo (api.ticino.ch) + eigene Ergänzungen",
        "events": data,
    }
    tmp = args.out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, args.out)  # erst ganz geschrieben, dann ersetzt
    print(f"OK – {args.out} geschrieben ({total} Events, Stand {payload['updated']})", file=sys.stderr)


if __name__ == "__main__":
    main()
