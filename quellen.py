"""
Zusätzliche Event-Quellen für «Eventi Lago Maggiore» (täglich automatisch).

Entscheid Michael 20.11.2026: «Bitte alles in der App hinzufügen sie ist ja nicht
komerziell» – die App ist nur für ihn und die Familie, nicht kommerziell; die
Quelle wird bei jedem Event angezeigt und verlinkt.

- Città di Locarno   https://www.locarno.ch/it/eventi              (Liste + Detailseiten)
- locarnese.events   https://www.locarnese.events/it/eventi/...    (Listen je Region + Detailseiten)
- Winterland         https://winterland.swiss/programm/?lang=de    (eine Programmseite)

Jede Quelle läuft für sich: Fehler = Quelle wird übersprungen, der Rest läuft weiter.
Doppelte Events (gleicher Ort, gleicher Tag, passende Zeit, ähnlicher Titel oder
gleicher genauer Ort) werden erkannt. Vorrang: Ticino-Schnittstelle, dann eigene
Ergänzungen, dann locarno.ch, locarnese.events, Winterland-Programm.
"""
import html
import re
import sys
import time
from datetime import date

import requests

UA = {"User-Agent": "Mozilla/5.0 (EventiLagoMaggiore/2.0; +https://kipferdp.github.io/eventi-lago-maggiore/)"}
PAUSE = 0.6  # Sekunden zwischen zwei Abfragen (Server schonen)
TOWNS = {"ascona": "Ascona", "locarno": "Locarno", "minusio": "Minusio",
         "tenero": "Tenero", "orselina": "Orselina", "muralto": "Muralto"}
# Orte ausserhalb der App: nennt ein Event nur solche, wird es weggelassen
OTHER_PLACES = ["camedo", "gordola", "verzasca", "brissago", "gambarogno", "losone", "ronco", "brione",
                "centovalli", "vallemaggia", "cevio", "maggia", "intragna", "tegna", "verscio", "cavigliano",
                "vira", "magadino", "cugnasco", "lavertezzo", "sonogno", "bellinzona", "lugano", "onsernone"]
# Koordinaten bekannter Orte (aus der Ticino-Schnittstelle, gleicher Ort bei anderem Event)
COORD = {
    "winterland_locarno": (46.1696052, 8.7960181),  # Piazza Grande, Locarno
    "largo_zorzi": (46.1698704, 8.79865),
    "sant_antonio": (46.169806, 8.7917285),
    "piazza_ascona": (46.1539078, 8.7688003),       # Piazza G. Motta, Ascona
    "lungolago_ascona": (46.1537368, 8.7689245),
}
WD = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _text(h):
    return _clean(re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", h))


def _get(session, url):
    r = session.get(url, headers=UA, timeout=40)
    r.raise_for_status()
    return r.content.decode("utf-8", "replace")


def _iso_dmy(dmy):
    d, m, y = dmy.split(".")
    return f"{y}-{m}-{d}"


def _fmt(iso, year=True):
    y, m, d = map(int, iso.split("-"))
    return f"{WD[date(y, m, d).weekday()]}, {d:02d}.{m:02d}." + (str(y) if year else "")


def _date_text(start, end):
    if end and end != start:
        return f"{_fmt(start, year=start[:4] != end[:4])} – {_fmt(end)}"
    return _fmt(start)


def _time_text(a, b):
    if a and b and a != b:
        return f"{a}–{b} Uhr"
    return f"{a} Uhr" if a else ""


# ---------------------------------------------------------------------------
# Kategorien aus Titeln (Italienisch/Deutsch)
# ---------------------------------------------------------------------------
KEYWORD_CATS = [
    (r"natal|christmas|weihnacht|avvento|advent|babbo|presepe|san nicolao|nikolaus", "weihnachten"),
    (r"capodanno|silvester|nuovo anno|neujahr|new year", "silvester"),
    (r"carneval|fasnacht|stranociada|risottata", "fasnacht"),
    (r"cinema|\bfilm|kino", "kino"),
    (r"concert|konzert|music|musik|orchestr|\bcoro\b|\bchor\b|jazz|tribut|\bdj\b|\blive\b|\bband\b|recital|organ", "musik"),
    (r"mostra|esposizion|ausstellung|collezione|vernissage", "ausstellung"),
    (r"mercat|markt|market", "markt"),
    (r"teatro|theater|spettacolo|danza|\btanz|ballet|commedia|cabaret|comedy", "kultur"),
    (r"bambin|kinder|\bkids\b|famigli|ragazz", "kinder"),
    (r"corsa|\brun\b|lauf|\bgara\b|torneo|marathon|triathlon", "sport"),
    (r"degustaz|gastronom|\bcena\b|brunch|aperitiv|apéro|\bvin[oi]\b|sagra|risotto|fondue", "kulinarik"),
    (r"conferenz|incontro|lettura|libro|vortrag|letteratura", "kultur"),
    (r"escursion|passeggiat|wanderung", "natur"),
    (r"workshop|\bcorso\b|laborator|\bkurs", "kurs"),
]
LEV_CATS = {
    "musica": "musik", "teatro e danza": "kultur", "mostre": "ausstellung", "vernissage": "ausstellung",
    "cinema": "kino", "famiglie": "kinder", "feste popolari": "tradition", "tradizioni": "tradition",
    "mercati": "markt", "gastronomia": "kulinarik", "sport": "sport", "natura": "natur",
    "escursioni e gite": "natur", "incontri e conferenze": "kultur", "letteratura": "kultur",
    "attività didattica": "kurs", "volontariato": "event",
}
FEST = {"weihnachten", "silvester", "fasnacht"}


def cats_for(title, extra=(), default="event"):
    t = (title or "").lower()
    found = []
    for pat, cat in KEYWORD_CATS:
        if re.search(pat, t) and cat not in found:
            found.append(cat)
    for c in extra:
        if c and c not in found:
            found.append(c)
    if default and default != "event" and default not in found:
        found.append(default)
    ordered = [c for c in found if c in FEST] + [c for c in found if c not in FEST]
    return ordered or [default or "event"]


# ---------------------------------------------------------------------------
# 1) Città di Locarno
# ---------------------------------------------------------------------------
SIMPLE_TIME = re.compile(r"(?i)(ore\s*)?\d{1,2}[.:]\d{2}(\s*(-|–|alle)\s*\d{1,2}[.:]\d{2})?")


def from_locarno(session, today):
    h = _get(session, "https://www.locarno.ch/it/eventi")
    out = []
    pat = re.compile(r'<div class="evento_data">(.*?)</div>\s*<div class="evento_testo">\s*<h3[^>]*>\s*'
                     r'<a href="(https://www\.locarno\.ch/it/eventi/[^"]+)"[^>]*>(.*?)</a>\s*</h3>\s*(?:<p>(.*?)</p>)?', re.S)
    for m in pat.finditer(h):
        dates = re.findall(r"<b>(\d{1,2})</b>\s*<br\s*/?>\s*(\d{2})\.(\d{4})", m.group(1))
        if not dates:
            continue
        start = f"{dates[0][2]}-{dates[0][1]}-{int(dates[0][0]):02d}"
        end = f"{dates[-1][2]}-{dates[-1][1]}-{int(dates[-1][0]):02d}"
        if end < today:
            continue
        url, title, venue = m.group(2), _clean(m.group(3)).strip(" -"), _clean(m.group(4) or "")
        if venue and any(o in venue.lower() for o in OTHER_PLACES) and "locarno" not in venue.lower():
            continue
        out.append({"uid": "locarnoch-" + url.rstrip("/").split("/")[-1][:80], "towns": ["locarno"],
                    "title": title, "start": start, "end": end, "from": "", "to": "",
                    "loc": venue if "locarno" in venue.lower() else (f"{venue}, Locarno" if venue else "Locarno"),
                    "link": url, "source": "Città di Locarno (locarno.ch)"})

    for e in out:  # Detailseite: Uhrzeit («Orari»), Eintritt («Entrata»)
        time.sleep(PAUSE)
        try:
            t = _text(_get(session, e["link"]))
        except Exception as ex:
            print(f"   locarno.ch Detail fehlt ({e['link']}): {ex}", file=sys.stderr)
            continue
        pos = t.find(e["title"][:25])
        t = t[pos:] if pos >= 0 else t
        mo = re.search(r"\bOrari (.*?) (?:Entrata|Maggiori informazioni|Contatti|Organizzatore)", t)
        if mo:
            orari = mo.group(1).strip()
            if SIMPLE_TIME.fullmatch(orari):
                tt = re.findall(r"(\d{1,2})[.:](\d{2})", orari)
                e["from"] = f"{int(tt[0][0]):02d}:{tt[0][1]}"
                if len(tt) > 1:
                    e["to"] = f"{int(tt[1][0]):02d}:{tt[1][1]}"
            elif orari:
                e["timeNote"] = orari[:160]
        me = re.search(r"\bEntrata (.*?) (?:Maggiori informazioni|Contatti|Organizzatore)", t)
        if me and me.group(1).strip():
            e["prices"] = [me.group(1).strip()[:160]]
    return out


# ---------------------------------------------------------------------------
# 2) locarnese.events (Ente Regionale per lo Sviluppo Locarnese e Vallemaggia)
# ---------------------------------------------------------------------------
LEV_REGIONS = {"ascona": "ascona", "locarno": "locarno", "minusio-e-brione-s-minusio": "minusio",
               "muralto-e-orselina": "muralto", "valle-verzasca-e-piano": None}
LEV_DATE = re.compile(r"^(\d{2}\.\d{2}\.\d{4})(?:\s*[–-]\s*(\d{2}\.\d{2}\.\d{4}))?(?:,\s*(\d{2}:\d{2})(?:\s*[–-]\s*(\d{2}:\d{2}))?)?$")


def lev_towns(region_town, place):
    """App-Orte eines Events aus Region und «place» (z. B. «Ascona Locarno», «Sala Congressi»)."""
    p = (place or "").lower()
    named = [k for k, name in TOWNS.items() if name.lower() in p]
    if named:
        return named
    if any(o in p for o in OTHER_PLACES) or not region_town:
        return []
    return [region_town]


def from_locarnese(session, today):
    found = {}
    for reg, region_town in LEV_REGIONS.items():
        try:
            h = _get(session, f"https://www.locarnese.events/it/eventi/ricerca/tutti/{reg}/prossimi/")
        except Exception as ex:
            print(f"   locarnese.events {reg} übersprungen: {ex}", file=sys.stderr)
            continue
        for m in re.finditer(r'<div class="event event-small">(.*?)<div class="place">(.*?)</div>', h, re.S):
            block, place = m.group(1), _clean(m.group(2))
            a = re.search(r'<h3><a href="(https://www\.locarnese\.events/it/eventi/(\d+)[^"]*)">(.*?)</a></h3>', block, re.S)
            d = re.search(r'<div class="date">(.*?)</div>', block, re.S)
            if not a or not d:
                continue
            dm = LEV_DATE.match(_clean(d.group(1)))
            if not dm:
                continue
            start = _iso_dmy(dm.group(1))
            end = _iso_dmy(dm.group(2)) if dm.group(2) else start
            if end < today:
                continue
            ev_id = a.group(2)
            e = found.get(ev_id)
            if not e:
                img = re.search(r"background-image:\s*url\(([^)]+)\)", block)
                catblock = re.search(r'<div class="categories">(.*?)</div>', block, re.S)
                cats = [LEV_CATS.get(_clean(c).lower(), "") for c in re.findall(r"<a [^>]*>(.*?)</a>", catblock.group(1), re.S)] if catblock else []
                e = {"uid": f"lev-{ev_id}", "towns": [], "title": _clean(a.group(3)), "start": start, "end": end,
                     "from": dm.group(3) or "", "to": dm.group(4) or "", "place": place, "link": a.group(1),
                     "image": img.group(1).strip("'\"") if img else "", "levcats": [c for c in cats if c],
                     "source": "locarnese.events (Ente Regionale per lo Sviluppo Locarnese e Vallemaggia)"}
                found[ev_id] = e
            for t in lev_towns(region_town, place):
                if t not in e["towns"]:
                    e["towns"].append(t)
        time.sleep(PAUSE)

    out = [e for e in found.values() if e["towns"]]
    for e in out:  # Detailseite: genauer Ort («Luogo»), Preise
        time.sleep(PAUSE)
        try:
            t = _text(_get(session, e["link"]))
        except Exception as ex:
            print(f"   locarnese Detail fehlt ({e['link']}): {ex}", file=sys.stderr)
            continue
        ml = re.search(r"\bLuogo (.*?) (?:Date|Data|Prezzi e prevendita|Meteo|Organizzazione|Informazioni|Contatti|Cosa|Quando)\b", t)
        if ml and 2 < len(ml.group(1).strip()) <= 90:
            e["address"] = ml.group(1).strip()
        mp = re.search(r"\bPrezzi e prevendita (.*?) (?:Meteo|Organizzazione|Informazioni|Contatti|Cosa|Quando)", t)
        if mp and mp.group(1).strip():
            e["prices"] = [mp.group(1).strip()[:160]]
    for e in out:
        town_name = TOWNS[e["towns"][0]]
        place = e["place"] if e["place"].lower() not in [n.lower() for n in TOWNS.values()] and \
            not all(w.lower() in [n.lower() for n in TOWNS.values()] for w in e["place"].split()) else ""
        parts = list(dict.fromkeys(p for p in [place, e.get("address")] if p))
        loc = ", ".join(parts)
        if loc and town_name.lower() not in loc.lower():
            loc += f", {town_name}"
        e["loc"] = loc or town_name
    return out


# ---------------------------------------------------------------------------
# 3) Winterland-Programm
# ---------------------------------------------------------------------------
WL_DAY = re.compile(r"^(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Samstag|Sonntag) (\d{2})\.(\d{2})-(\d{2})$")
WL_TIME = re.compile(r"^(\d{2}:\d{2})(?:\s*[-–]\s*(\d{2}:\d{2}))?$")


def _wl_place(ort, venue):
    v = venue.lower()
    if ort == "Locarno":
        if "zorzi" in v:
            return f"{venue}, Locarno", COORD["largo_zorzi"]
        if "antonio" in v:
            return f"{venue}, Locarno", COORD["sant_antonio"]
        if "città vecchia" in v or "citta vecchia" in v:
            return (venue if "locarno" in v else f"{venue}, Locarno"), None
        return f"{venue}, Winterland Locarno", COORD["winterland_locarno"]
    if "piazza" in v:
        return "Piazza Giuseppe Motta, Ascona", COORD["piazza_ascona"]
    if "lake dome" in v:
        return "Lake Dome, Piazza Torre, Ascona", None
    if "eis" in v or "ice" in v:
        return f"{venue}, Seepromenade Ascona", COORD["lungolago_ascona"]
    return f"{venue}, Ascona", None


def from_winterland(session, today):
    h = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", _get(session, "https://winterland.swiss/programm/?lang=de"))
    toks = [x.strip() for x in re.split(r"\s*\|\s*", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " | ", h)))) if x.strip()]
    out, seen, cur, i = [], set(), None, 0
    while i < len(toks):
        m = WL_DAY.match(toks[i])
        if m:
            cur = f"20{m.group(4)}-{m.group(3)}-{m.group(2)}"
            i += 1
            continue
        if cur and toks[i] in ("Ascona", "Locarno") and i + 3 < len(toks) and WL_TIME.match(toks[i + 2]):
            ort, venue, tm, title = toks[i], toks[i + 1], WL_TIME.match(toks[i + 2]), toks[i + 3]
            sub = toks[i + 4] if i + 4 < len(toks) else ""
            if WL_DAY.match(sub) or sub in ("Ascona", "Locarno") or WL_TIME.match(sub) or len(sub) < 3:
                sub = ""
            uid = "wl-" + re.sub(r"[^a-z0-9]+", "-", f"{cur}-{ort}-{tm.group(1)}-{title}".lower()).strip("-")[:100]
            if cur >= today and uid not in seen:
                seen.add(uid)
                loc, coord = _wl_place(ort, venue)
                out.append({"uid": uid, "towns": [ort.lower()], "title": title, "start": cur, "end": cur,
                            "from": tm.group(1), "to": tm.group(2) or "", "loc": loc,
                            "lat": coord[0] if coord else None, "lng": coord[1] if coord else None,
                            "summary": sub[:300], "parent": "Winterland 2026/27",
                            "link": "https://winterland.swiss/programm/?lang=de",
                            "website": "https://winterland.swiss/?lang=de", "default_cat": "weihnachten",
                            "keywords": "Winterland Programm",
                            "source": "Winterland Ascona-Locarno (winterland.swiss)"})
            i += 4
            continue
        i += 1
    return out


# ---------------------------------------------------------------------------
# Doppel-Erkennung
# ---------------------------------------------------------------------------
STOP = set(("il lo la le i gli un una uno di del della dello dei degli delle e ed a al alla allo ai agli alle in con "
            "per da dal dalla su sul sulla tra fra the of and der die das und mit im am von zu fur fuer auf an ein "
            "eine des dem den au du de et les ore uhr").split())
TOWN_WORDS = {n.lower() for n in TOWNS.values()} | {"winterland"}
GENERIC_PLACE = {"via", "viale", "piazza", "largo", "chiesa", "sala", "centro", "teatro", "lungolago", "contrada"}


def _norm(s):
    s = (s or "").lower().replace("ß", "ss")
    for a, b in (("àáâä", "a"), ("èéêë", "e"), ("ìíîï", "i"), ("òóôö", "o"), ("ùúûü", "u")):
        s = re.sub(f"[{a}]", b, s)
    return re.sub(r"[^a-z0-9]+", " ", s).split()


def tokens(s):
    out = []
    for t in _norm(s):
        if t[0].isdigit():
            t = re.match(r"\d+", t).group(0)
            if re.fullmatch(r"(19|20)\d\d", t):
                continue
        if t in STOP or (len(t) < 3 and not t.isdigit()):
            continue
        out.append(t)
    return out


def _tok_match(a, b):
    if a == b:
        return True
    if a.isdigit() or b.isdigit():
        return False
    n = min(len(a), len(b))
    k = max(4, n - 2)
    return n >= 4 and a[:k] == b[:k]


def similarity(ta, tb):
    sa, sb = set(ta), set(tb)
    if not sa or not sb:
        return 0.0
    hits = sum(1 for a in sa if any(_tok_match(a, b) for b in sb))
    return hits / min(len(sa), len(sb))


def _anchor(e, today):
    ds = e.get("dates") or [{"start": e.get("start"), "end": e.get("end") or e.get("start"), "from": ""}]
    for o in ds:
        if (o.get("end") or o.get("start")) >= today:
            return o.get("start"), o.get("from") or ""
    return ds[0].get("start"), ds[0].get("from") or ""


def is_duplicate(a, b, today):
    """a, b = Events im App-Format am selben Ort."""
    sa, fa = _anchor(a, today)
    sb, fb = _anchor(b, today)
    if sa != sb or (fa and fb and fa != fb):
        return False
    both_times = bool(fa and fb)
    s = similarity(tokens(a.get("title")), tokens(b.get("title")))
    if s >= 0.5 or (s >= 0.3 and both_times):
        return True
    pa = [t for t in tokens(a.get("loc")) if t not in TOWN_WORDS and t not in GENERIC_PLACE]
    pb = [t for t in tokens(b.get("loc")) if t not in TOWN_WORDS and t not in GENERIC_PLACE]
    return bool(both_times and pa and pb and similarity(pa, pb) >= 0.5)


# ---------------------------------------------------------------------------
# In die App-Daten einfügen
# ---------------------------------------------------------------------------
def to_app(e, town, labels):
    cats = cats_for(e["title"], extra=e.get("levcats") or (), default=e.get("default_cat", "event"))
    cat = cats[0]
    ev = {
        "id": e["uid"], "uid": e["uid"], "city": town, "title": e["title"],
        "cat": cat, "catLabel": labels.get(cat, cat.capitalize()), "cats": cats,
        "start": e["start"], "end": e["end"],
        "dates": [{"start": e["start"], "end": e["end"], "from": e.get("from", ""), "to": e.get("to", "")}],
        "dateText": _date_text(e["start"], e["end"]),
        "timeText": _time_text(e.get("from", ""), e.get("to", "")) or e.get("timeNote", ""),
        "sortKey": 0, "loc": e.get("loc") or TOWNS[town], "lat": e.get("lat"), "lng": e.get("lng"),
        "image": e.get("image", ""), "link": e.get("link", ""), "isTop": False,
        "parent": e.get("parent", ""), "summary": e.get("summary", ""),
        "keywords": e.get("keywords", ""), "source": e["source"],
    }
    for k in ("prices", "website"):
        if e.get(k):
            ev[k] = e[k]
    return ev


SOURCES = [("locarno.ch", from_locarno), ("locarnese.events", from_locarnese), ("winterland.swiss", from_winterland)]


def add_sources(out, today_iso, labels, only=None):
    session = requests.Session()
    stats = {}
    for name, fn in SOURCES:
        if only and name not in only:
            continue
        try:
            items = fn(session, today_iso)
        except Exception as ex:
            print(f"-> Quelle {name} übersprungen: {ex}", file=sys.stderr)
            stats[name] = "Fehler"
            continue
        added = dup = 0
        for e in items:
            for town in e["towns"]:
                if town not in out:
                    continue
                ev = to_app(e, town, labels)
                if any(x["uid"] == ev["uid"] for x in out[town]):
                    continue
                if any(is_duplicate(ev, x, today_iso) for x in out[town]):
                    dup += 1
                    continue
                out[town].append(ev)
                added += 1
        stats[name] = f"{len(items)} gelesen, {added} neu, {dup} doppelt"
        print(f"-> Quelle {name}: {stats[name]}", file=sys.stderr)
    return stats
