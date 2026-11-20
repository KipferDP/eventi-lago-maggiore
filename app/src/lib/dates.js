// Datums-Helfer. Alle Daten sind ISO-Texte 'JJJJ-MM-TT' (Ortszeit Schweiz).

const WD = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa']

/** Heutiges Datum in der Schweiz als 'JJJJ-MM-TT' (unabhängig von der Gerätezeitzone). */
export function todayZurich(now = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Zurich', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now)
  const get = (t) => parts.find((p) => p.type === t).value
  return `${get('year')}-${get('month')}-${get('day')}`
}

function toUTC(iso) {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d)
}

export function addDays(iso, n) {
  const t = new Date(toUTC(iso) + n * 86400000)
  return t.toISOString().slice(0, 10)
}

export function weekday(iso) {
  return new Date(toUTC(iso)).getUTCDay() // 0 = Sonntag
}

export function daysBetween(a, b) {
  return Math.round((toUTC(b) - toUTC(a)) / 86400000)
}

/** 'Fr, 20.11.' */
export function fmtShort(iso) {
  const [, m, d] = iso.split('-')
  return `${WD[weekday(iso)]}, ${d}.${m}.`
}

/** '06.01.2027' */
export function fmtLong(iso) {
  const [y, m, d] = iso.split('-')
  return `${d}.${m}.${y}`
}

/** Überschrift einer Tagesgruppe: 'Heute', 'Morgen' oder 'Sa, 21.11.' */
export function dayLabel(iso, today) {
  if (iso === today) return 'Heute'
  if (iso === addDays(today, 1)) return 'Morgen'
  return fmtShort(iso)
}

/** Alle Termine eines Events als Liste {start, end, from, to}. */
export function occurrences(e) {
  if (Array.isArray(e.dates) && e.dates.length) return e.dates
  return [{ start: e.start, end: e.end || e.start, from: '', to: '' }]
}

/** Ende des letzten Termins. */
export function lastDay(e) {
  return occurrences(e).reduce((max, o) => (o.end > max ? o.end : max), e.end || e.start)
}

export function isPast(e, today) {
  return lastDay(e) < today
}

/** Nächster (oder laufender) Termin ab heute, sonst null. */
export function nextOccurrence(e, today) {
  const list = occurrences(e).filter((o) => o.end >= today)
  return list.length ? list[0] : null
}

/** Läuft schon (hat vor heute begonnen) und ist noch nicht vorbei. */
export function isOngoing(e, today) {
  const o = nextOccurrence(e, today)
  return !!o && o.start < today && o.end >= today
}

/** Findet an mindestens einem Tag im Bereich [from, to] statt. */
export function overlaps(e, from, to) {
  return occurrences(e).some((o) => o.start <= to && o.end >= from)
}

/** Zeitraum-Filter: gibt [von, bis] zurück oder null (= alle). */
export function rangeFor(key, today) {
  switch (key) {
    case 'heute':
      return [today, today]
    case 'wochenende': {
      const wd = weekday(today) // 0 So … 6 Sa
      if (wd === 0) return [today, today]
      if (wd === 5 || wd === 6) return [today, addDays(today, 7 - wd)]
      return [addDays(today, 5 - wd), addDays(today, 7 - wd)]
    }
    case '7':
      return [today, addDays(today, 6)]
    case '30':
      return [today, addDays(today, 29)]
    default:
      return null
  }
}

/** Datum und Zeit des nächsten Termins für die Karte, z. B. 'Fr, 20.11. · 21:00 Uhr'. */
export function cardDate(e, today) {
  const o = nextOccurrence(e, today)
  if (!o) return e.dateText || ''
  if (o.start < today && o.end >= today) return `bis ${fmtLong(lastDay(e))}`
  let txt = o.end && o.end !== o.start ? `${fmtShort(o.start)} – ${fmtShort(o.end)}` : fmtShort(o.start)
  if (o.from) txt += ` · ${o.from} Uhr`
  return txt
}

/** Anzahl weiterer Termine nach dem nächsten. */
export function moreDates(e, today) {
  const list = occurrences(e).filter((o) => o.end >= today)
  return Math.max(0, list.length - 1)
}
