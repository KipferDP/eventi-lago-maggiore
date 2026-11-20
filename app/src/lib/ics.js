// Kalender-Datei (.ics) für ein Event erzeugen (RFC 5545).
import { addDays, occurrences } from './dates.js'

const VTIMEZONE = [
  'BEGIN:VTIMEZONE',
  'TZID:Europe/Zurich',
  'BEGIN:DAYLIGHT',
  'TZOFFSETFROM:+0100',
  'TZOFFSETTO:+0200',
  'TZNAME:CEST',
  'DTSTART:19700329T020000',
  'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU',
  'END:DAYLIGHT',
  'BEGIN:STANDARD',
  'TZOFFSETFROM:+0200',
  'TZOFFSETTO:+0100',
  'TZNAME:CET',
  'DTSTART:19701025T030000',
  'RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU',
  'END:STANDARD',
  'END:VTIMEZONE',
]

export function escapeText(s) {
  return String(s || '')
    .replace(/\\/g, '\\\\')
    .replace(/\n/g, '\\n')
    .replace(/,/g, '\\,')
    .replace(/;/g, '\\;')
}

// Zeilen über 75 Byte falten (RFC 5545, 3.1); Umlaute zählen als 2 Byte und
// werden nie zerschnitten. Folgezeilen beginnen mit einem Leerzeichen.
const enc = new TextEncoder()
export function fold(line) {
  const out = []
  let cur = ''
  let bytes = 0
  for (const ch of line) {
    const b = enc.encode(ch).length
    const limit = out.length ? 74 : 75
    if (bytes + b > limit) {
      out.push(cur)
      cur = ch
      bytes = b
    } else {
      cur += ch
      bytes += b
    }
  }
  out.push(cur)
  return out.join('\r\n ')
}

const compact = (iso) => iso.replace(/-/g, '')
const hhmm = (t) => t.replace(':', '') + '00'
const validTime = (t) => /^\d{2}:\d{2}$/.test(t || '')

export function buildIcs(e, { cityName = '', url = '', now = new Date() } = {}) {
  const stamp = now.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '')
  const descParts = [e.summary, e.timeText, e.note, url].filter(Boolean)
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Eventi Lago Maggiore//DE', 'CALSCALE:GREGORIAN']
  let needsTz = false
  const events = []
  occurrences(e).forEach((o, i) => {
    const ev = ['BEGIN:VEVENT', `UID:${e.uid || e.id}-${i}@eventi-lago-maggiore`, `DTSTAMP:${stamp}`]
    const single = !o.end || o.end === o.start
    if (single && validTime(o.from)) {
      needsTz = true
      ev.push(`DTSTART;TZID=Europe/Zurich:${compact(o.start)}T${hhmm(o.from)}`)
      if (validTime(o.to) && o.to !== o.from) {
        const endDay = o.to < o.from ? addDays(o.start, 1) : o.start // z. B. bis 02:00 = nächster Tag
        ev.push(`DTEND;TZID=Europe/Zurich:${compact(endDay)}T${hhmm(o.to)}`)
      }
    } else {
      ev.push(`DTSTART;VALUE=DATE:${compact(o.start)}`)
      ev.push(`DTEND;VALUE=DATE:${compact(addDays(o.end || o.start, 1))}`)
    }
    ev.push(`SUMMARY:${escapeText(e.title)}`)
    ev.push(`LOCATION:${escapeText(e.loc || cityName)}`)
    if (descParts.length) ev.push(`DESCRIPTION:${escapeText(descParts.join('\n'))}`)
    if (url) ev.push(`URL:${url}`)
    ev.push('END:VEVENT')
    events.push(...ev)
  })
  if (needsTz) lines.push(...VTIMEZONE)
  lines.push(...events, 'END:VCALENDAR')
  return lines.map(fold).join('\r\n') + '\r\n'
}
