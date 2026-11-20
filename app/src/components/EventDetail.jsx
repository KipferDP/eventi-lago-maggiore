import { useEffect, useRef, useState } from 'react'
import { APP_URL, CITY_NAME, COVER, catInfo } from '../constants.js'
import { fmtShort, isOngoing, occurrences } from '../lib/dates.js'
import { buildIcs } from '../lib/ics.js'
import { hashFor } from '../lib/route.js'

const DESC_PREVIEW_CHARS = 520

function hostOf(url) {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

function slugify(s) {
  return String(s || 'event').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 50) || 'event'
}

function Row({ icon, label, children }) {
  return (
    <div className="info-row">
      <span className="ic" aria-hidden="true">{icon}</span>
      <div>
        <div className="t">{label}</div>
        <div className="v">{children}</div>
      </div>
    </div>
  )
}

export default function EventDetail({ event: e, cities, today, updated, isSaved, onToggleSaved, onClose, onOtherCity, onToast }) {
  const [fullDesc, setFullDesc] = useState(false)
  const backRef = useRef(null)
  const sheetRef = useRef(null)

  // Hintergrund nicht mitscrollen, Fokus auf «Zurück», Esc schliesst
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    backRef.current?.focus({ preventScroll: true })
    const onKey = (ev) => { if (ev.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
  }, [onClose])

  useEffect(() => {
    setFullDesc(false)
    sheetRef.current?.parentElement?.scrollTo?.(0, 0)
  }, [e && e.uid, e && e.city])

  if (!e) {
    return (
      <div className="detail" role="dialog" aria-modal="true" aria-label="Event nicht gefunden">
        <div className="hero plain">
          <button type="button" className="back" ref={backRef} onClick={onClose}><b aria-hidden="true">‹</b> Zurück</button>
        </div>
        <div className="sheet">
          <h2>Dieses Event gibt es nicht mehr</h2>
          <p className="hint">Es ist vorbei oder wurde vom Veranstalter entfernt. Alle aktuellen Events findest du in der Agenda.</p>
          <button type="button" className="cta" onClick={onClose}>Zur Agenda</button>
        </div>
      </div>
    )
  }

  const c = catInfo(e.cat)
  const ongoing = isOngoing(e, today)
  const shareUrl = APP_URL + hashFor({ view: 'detail', city: e.city, id: e.id })
  const upcoming = occurrences(e).filter((o) => o.end >= today)
  const desc = e.desc || []
  const descChars = desc.join(' ').length
  const descShown = fullDesc || descChars <= DESC_PREVIEW_CHARS ? desc : null
  const otherCities = (cities || []).filter((k) => k !== e.city)
  // Karte: mit Koordinaten genau, sonst Suche nach dem Ortstext (Google entscheidet)
  const mapUrl = e.lat && e.lng
    ? `https://www.google.com/maps/search/?api=1&query=${e.lat},${e.lng}`
    : e.loc ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(e.loc)}` : ''

  async function share() {
    const text = `${e.title} – ${e.dateText}${e.loc ? ` – ${e.loc}` : ''}`
    if (navigator.share) {
      try {
        await navigator.share({ title: e.title, text, url: shareUrl })
        return
      } catch (err) {
        if (err && err.name === 'AbortError') return
      }
    }
    try {
      await navigator.clipboard.writeText(shareUrl)
      onToast('Link kopiert – jetzt z. B. in WhatsApp einfügen')
    } catch {
      onToast(shareUrl)
    }
  }

  function addToCalendar() {
    const ics = buildIcs(e, { cityName: CITY_NAME[e.city], url: shareUrl })
    const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${slugify(e.title)}.ics`
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(a.href), 10000)
    onToast('Kalender-Datei erstellt')
  }

  return (
    <div className="detail" role="dialog" aria-modal="true" aria-labelledby="d-title">
      <div className="hero">
        <img src={e.imageLarge || e.image || COVER[e.city]} alt="" onError={(ev) => { ev.currentTarget.src = COVER[e.city] }} />
        <button type="button" className="back" ref={backRef} onClick={onClose}><b aria-hidden="true">‹</b> Zurück</button>
        <div className="hero-actions">
          <button type="button" className="round light" onClick={share} aria-label="Event teilen" title="Teilen">⤴</button>
          <button type="button" className={`round light${isSaved ? ' on' : ''}`} onClick={() => onToggleSaved(e.uid)} aria-pressed={isSaved} aria-label={isSaved ? 'Von der Merkliste entfernen' : 'Merken'} title="Merken">
            {isSaved ? '♥' : '♡'}
          </button>
        </div>
      </div>

      <div className="sheet" ref={sheetRef}>
        <div className="badges">
          {(e.cats || [e.cat]).slice(0, 3).map((k) => {
            const ci = catInfo(k)
            return <span key={k} className="d-badge" style={{ background: ci.color }}>{ci.icon} {ci.label}</span>
          })}
          {e.isTop && <span className="d-badge top">★ Highlight</span>}
          {ongoing && <span className="d-badge live">● läuft</span>}
          {e.cancelled && <span className="d-badge cancelled">Abgesagt</span>}
        </div>

        <h2 id="d-title">{e.title}</h2>
        {e.summary && <p className="lead">{e.summary}</p>}
        {e.cancelled && e.cancelledText && <p className="note warn">{e.cancelledText}</p>}
        {e.note && <p className="note">ℹ️ {e.note}</p>}

        <Row icon="📅" label="Datum">{e.dateText}</Row>
        {upcoming.length > 1 ? (
          <Row icon="🕒" label={`${upcoming.length} Termine`}>
            <ul className="dates">
              {upcoming.map((o) => (
                <li key={o.start + o.from}>{fmtShort(o.start)}{o.end !== o.start ? ` – ${fmtShort(o.end)}` : ''}{o.from ? ` · ${o.from}${o.to && o.to !== o.from ? `–${o.to}` : ''} Uhr` : ''}</li>
              ))}
            </ul>
          </Row>
        ) : e.timeText ? (
          <Row icon="🕒" label="Zeit">{e.timeText}</Row>
        ) : null}
        <Row icon="📍" label="Ort">
          {e.loc || CITY_NAME[e.city]}
          {mapUrl && <> · <a href={mapUrl} target="_blank" rel="noopener noreferrer">Karte</a></>}
        </Row>
        {otherCities.length > 0 && (
          <Row icon="🔁" label="Auch in">
            {otherCities.map((k) => (
              <button type="button" key={k} className="fchip on small" onClick={() => onOtherCity(k)}>{CITY_NAME[k]} ›</button>
            ))}
          </Row>
        )}
        {e.parent && <Row icon="🎪" label="Teil von">{e.parent}</Row>}
        {e.prices && e.prices.length > 0 && (
          <Row icon="💶" label="Eintritt">{e.prices.map((p) => <div key={p}>{p}</div>)}</Row>
        )}
        {e.recurringText && <Row icon="🗓️" label="Findet statt">{e.recurringText}</Row>}
        {e.organizer && <Row icon="🏢" label="Veranstalter">{e.organizer}</Row>}
        {(e.phone || e.email) && (
          <Row icon="☎️" label="Kontakt">
            {e.phone && <div><a href={`tel:${e.phone.replace(/\s+/g, '')}`}>{e.phone}</a></div>}
            {e.email && <div><a href={`mailto:${e.email}`}>{e.email}</a></div>}
          </Row>
        )}

        {desc.length > 0 && (
          <div className="desc">
            <h3>Beschreibung</h3>
            {descShown
              ? descShown.map((p, i) => <p key={i}>{p}</p>)
              : <p>{desc.join(' ').slice(0, DESC_PREVIEW_CHARS).replace(/\s+\S*$/, '')} …</p>}
            {!descShown && (
              <button type="button" className="link-btn" onClick={() => setFullDesc(true)}>Ganze Beschreibung lesen</button>
            )}
            {descShown && e.descLinks && e.descLinks.length > 0 && (
              <ul className="desc-links">
                {e.descLinks.map((l) => <li key={l.url}><a href={l.url} target="_blank" rel="noopener noreferrer">{l.label}</a></li>)}
              </ul>
            )}
          </div>
        )}

        <div className="actions">
          {e.tickets && <a className="cta" href={e.tickets.url} target="_blank" rel="noopener noreferrer">🎟️ {e.tickets.label}</a>}
          {e.website && <a className={`cta${e.tickets ? ' ghost' : ''}`} href={e.website} target="_blank" rel="noopener noreferrer">🌐 Website: {hostOf(e.website)}</a>}
          {e.link && <a className="cta ghost" href={e.link} target="_blank" rel="noopener noreferrer">ℹ️ Seite bei {hostOf(e.link)}</a>}
          {mapUrl && <a className="cta ghost" href={mapUrl} target="_blank" rel="noopener noreferrer">🗺️ Auf Karte zeigen</a>}
          <button type="button" className="cta ghost" onClick={addToCalendar}>📆 In Kalender eintragen</button>
          {e.video && <a className="cta ghost" href={e.video} target="_blank" rel="noopener noreferrer">▶️ Video ansehen</a>}
          <button type="button" className="cta ghost" onClick={share}>⤴ Event teilen</button>
          <button type="button" className="cta ghost" onClick={() => onToggleSaved(e.uid)}>{isSaved ? '♥ Gemerkt (entfernen)' : '♡ Merken'}</button>
        </div>

        <p className="source">Quelle: {e.source || 'Ticino Turismo'}{updated ? ` · Stand ${updated}` : ''}</p>
      </div>
    </div>
  )
}
