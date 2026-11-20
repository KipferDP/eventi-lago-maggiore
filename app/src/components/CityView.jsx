import { useMemo, useState } from 'react'
import { CATEGORIES, CITY_NAME, RANGES, catInfo } from '../constants.js'
import { addDays, dayLabel, occurrences, overlaps, rangeFor, nextOccurrence, fmtShort } from '../lib/dates.js'
import { EventRow, HighlightCard } from './EventRow.jsx'

const ONGOING_PREVIEW = 4
const HIGHLIGHT_DAYS = 120

// Sortierschlüssel für Uhrzeiten: Nacht-Termine (00:00–04:59) gehören ans Ende des Tages
function timeKey(t) {
  if (!t) return '99'
  return t < '05:00' ? `3${t}` : `1${t}`
}

// Termin, der für die Einordnung zählt: erster Termin ab Beginn des Zeitraums
function anchorOccurrence(e, from, to) {
  return occurrences(e).find((o) => o.end >= from && (!to || o.start <= to)) || null
}

export default function CityView({ city, events, today, filters, setFilters, saved, onOpen }) {
  const [showAllOngoing, setShowAllOngoing] = useState(false)
  const { range, cat } = filters
  const rng = rangeFor(range, today)
  const from = rng ? rng[0] : today
  const to = rng ? rng[1] : null

  const inRange = useMemo(
    () => events.filter((e) => !to || overlaps(e, from, to)),
    [events, from, to],
  )

  const catCounts = useMemo(() => {
    const m = new Map()
    for (const e of inRange) for (const k of e.cats || [e.cat]) m.set(k, (m.get(k) || 0) + 1)
    return [...m.entries()].sort((a, b) => b[1] - a[1] || catInfo(a[0]).label.localeCompare(catInfo(b[0]).label))
  }, [inRange])

  const filtered = cat === 'alle' ? inRange : inRange.filter((e) => (e.cats || [e.cat]).includes(cat))

  // Highlights: Top-Events, die laufen oder in den nächsten 120 Tagen beginnen
  // (mindestens 3, falls vorhanden, damit die Leiste nie leer wirkt)
  const highlights = useMemo(() => {
    if (range !== 'alle' || cat !== 'alle') return []
    const limit = addDays(today, HIGHLIGHT_DAYS)
    const all = events
      .filter((e) => e.isTop)
      .map((e) => ({ e, o: nextOccurrence(e, today) }))
      .filter((x) => x.o)
      .sort((a, b) => (a.o.start < today ? today : a.o.start).localeCompare(b.o.start < today ? today : b.o.start))
    const soon = all.filter((x) => x.o.start <= limit)
    return (soon.length >= 3 ? soon : all.slice(0, Math.max(3, soon.length))).slice(0, 10).map((x) => x.e)
  }, [events, range, cat, today])

  // Gruppen: «läuft schon» + je Tag
  const { ongoing, days } = useMemo(() => {
    const ongoingList = []
    const dayMap = new Map()
    for (const e of filtered) {
      const o = anchorOccurrence(e, from, to)
      if (!o) continue
      if (o.start < from) ongoingList.push({ e, o })
      else {
        if (!dayMap.has(o.start)) dayMap.set(o.start, [])
        dayMap.get(o.start).push({ e, o })
      }
    }
    ongoingList.sort((a, b) => (b.e.isTop - a.e.isTop) || a.o.end.localeCompare(b.o.end) || a.e.title.localeCompare(b.e.title))
    const dayList = [...dayMap.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([day, list]) => [day, list.sort((a, b) => timeKey(a.o.from).localeCompare(timeKey(b.o.from)) || (b.e.isTop - a.e.isTop) || a.e.title.localeCompare(b.e.title))])
    return { ongoing: ongoingList, days: dayList }
  }, [filtered, from, to])

  const set = (patch) => {
    setShowAllOngoing(false)
    setFilters({ range, cat, ...patch })
  }
  const ongoingShown = showAllOngoing ? ongoing : ongoing.slice(0, ONGOING_PREVIEW)
  const savedSet = new Set(saved)
  const empty = ongoing.length === 0 && days.length === 0

  return (
    <div className="list">
      {highlights.length > 0 && (
        <section className="hl" aria-label={`Highlights in ${CITY_NAME[city]}`}>
          <h2 className="sec">★ Highlights</h2>
          <div className="hl-scroll">
            {highlights.map((e) => <HighlightCard key={e.uid} e={e} today={today} onOpen={onOpen} />)}
          </div>
        </section>
      )}

      <div className="filters" role="group" aria-label="Filter">
        <div className="chips">
          {RANGES.map((r) => (
            <button type="button" key={r.key} className={`fchip${range === r.key ? ' on' : ''}`} aria-pressed={range === r.key} onClick={() => set({ range: r.key })}>
              {r.label}
            </button>
          ))}
        </div>
        {catCounts.length > 1 && (
          <div className="chips">
            <button type="button" className={`fchip${cat === 'alle' ? ' on' : ''}`} aria-pressed={cat === 'alle'} onClick={() => set({ cat: 'alle' })}>
              Alle Kategorien
            </button>
            {catCounts.map(([k, n]) => (
              <button type="button" key={k} className={`fchip${cat === k ? ' on' : ''}`} aria-pressed={cat === k} onClick={() => set({ cat: k })}>
                {(CATEGORIES[k] || catInfo(k)).icon} {catInfo(k).label} <span className="n">{n}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {empty && (
        <div className="empty">
          <p>Keine Events {range !== 'alle' ? 'in diesem Zeitraum' : ''}{cat !== 'alle' ? ' in dieser Kategorie' : ''}.</p>
          {(range !== 'alle' || cat !== 'alle') && (
            <button type="button" className="link-btn" onClick={() => set({ range: 'alle', cat: 'alle' })}>Filter zurücksetzen</button>
          )}
        </div>
      )}

      {ongoing.length > 0 && (
        <section aria-label="Läuft gerade">
          <h2 className="sec">{rng && rng[0] !== today ? `Läuft schon vor ${fmtShort(rng[0])}` : 'Läuft gerade'} <span className="n">{ongoing.length}</span></h2>
          {ongoingShown.map(({ e }) => (
            <EventRow key={e.uid} e={e} today={today} saved={savedSet.has(e.uid)} onOpen={onOpen} />
          ))}
          {ongoing.length > ONGOING_PREVIEW && (
            <button type="button" className="more-btn" onClick={() => setShowAllOngoing((v) => !v)}>
              {showAllOngoing ? 'Weniger anzeigen' : `Alle ${ongoing.length} laufenden Events anzeigen`}
            </button>
          )}
        </section>
      )}

      {days.map(([day, list]) => (
        <section key={day} aria-label={dayLabel(day, today)}>
          <h2 className="sec">
            {dayLabel(day, today)}
            {dayLabel(day, today) !== fmtShort(day) && <span className="sub"> · {fmtShort(day)}</span>}
          </h2>
          {list.map(({ e }) => (
            <EventRow key={e.uid} e={e} today={today} saved={savedSet.has(e.uid)} onOpen={onOpen} />
          ))}
        </section>
      ))}
    </div>
  )
}
