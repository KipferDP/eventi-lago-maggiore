import { catInfo, COVER, CITY_NAME } from '../constants.js'
import { cardDate, isOngoing, moreDates } from '../lib/dates.js'

function fallback(ev, city) {
  const img = ev.currentTarget
  const cover = COVER[city] || COVER.locarno
  if (!img.src.endsWith(cover)) img.src = cover
}

/** Kompakte Zeile in der Liste. */
export function EventRow({ e, today, saved, cities, onOpen }) {
  const c = catInfo(e.cat)
  const ongoing = isOngoing(e, today)
  const more = moreDates(e, today)
  return (
    <button type="button" className={`row${e.isTop ? ' is-top' : ''}`} onClick={() => onOpen(e)}>
      <img className="thumb" src={e.image || COVER[e.city]} alt="" loading="lazy" decoding="async" onError={(ev) => fallback(ev, e.city)} />
      <span className="row-body">
        <span className="row-date">
          {ongoing && <span className="live">● läuft</span>}
          {e.cancelled && <span className="cancelled">Abgesagt</span>}
          <span>{cardDate(e, today)}</span>
        </span>
        <span className="row-title">{e.title}</span>
        <span className="row-meta">📍 {e.loc}</span>
        <span className="row-tags">
          <span className="chip" style={{ background: c.color }}>{c.icon} {e.catLabel || c.label}</span>
          {e.isTop && <span className="chip top">★ Highlight</span>}
          {more > 0 && <span className="chip soft">+{more} {more === 1 ? 'Termin' : 'Termine'}</span>}
          {cities && cities.map((k) => <span key={k} className="chip city">{CITY_NAME[k]}</span>)}
          {saved && <span className="chip saved" aria-label="gemerkt">♥</span>}
        </span>
      </span>
    </button>
  )
}

/** Grosse Karte für die Highlights oben. */
export function HighlightCard({ e, today, onOpen }) {
  const c = catInfo(e.cat)
  const ongoing = isOngoing(e, today)
  return (
    <button type="button" className="hl-card" onClick={() => onOpen(e)}>
      <span className="hl-img">
        <img src={e.imageLarge || e.image || COVER[e.city]} alt="" loading="lazy" decoding="async" onError={(ev) => fallback(ev, e.city)} />
        <span className="badge" style={{ background: c.color }}>{c.icon} {e.catLabel || c.label}</span>
        <span className="top-badge">★ Highlight</span>
      </span>
      <span className="hl-body">
        <span className="row-date">
          {ongoing && <span className="live">● läuft</span>}
          <span>{cardDate(e, today)}</span>
        </span>
        <span className="hl-title">{e.title}</span>
        <span className="row-meta">📍 {e.loc}</span>
      </span>
    </button>
  )
}
