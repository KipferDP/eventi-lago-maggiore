import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { CITIES, CITY_NAME } from './constants.js'
import { todayZurich, isPast, nextOccurrence } from './lib/dates.js'
import { haystack } from './lib/search.js'
import { parseHash, hashFor } from './lib/route.js'
import { loadSaved, storeSaved } from './lib/storage.js'
import Header from './components/Header.jsx'
import CityView from './components/CityView.jsx'
import SearchView from './components/SearchView.jsx'
import SavedView from './components/SavedView.jsx'
import EventDetail from './components/EventDetail.jsx'
import Footer from './components/Footer.jsx'
import { Loading, LoadError } from './components/States.jsx'

const RELOAD_AFTER_MS = 3 * 60 * 60 * 1000 // nach 3 Stunden im Hintergrund neu laden

async function fetchEvents() {
  const res = await fetch(`./events.json?t=${Date.now()}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const json = await res.json()
  if (!json || typeof json.events !== 'object') throw new Error('Unbekanntes Datenformat')
  return json
}

function useHashRoute() {
  const [route, setRoute] = useState(() => parseHash(window.location.hash))
  useEffect(() => {
    const on = () => setRoute(parseHash(window.location.hash))
    window.addEventListener('hashchange', on)
    window.addEventListener('popstate', on)
    return () => {
      window.removeEventListener('hashchange', on)
      window.removeEventListener('popstate', on)
    }
  }, [])
  return route
}

// Navigation innerhalb der App. Selbst angelegte Verlaufseinträge bekommen
// { inApp: true }: dann führt «Zurück» sicher wieder in die App statt hinaus.
function navigate(r, { replace = false } = {}) {
  const h = hashFor(r)
  if (replace) {
    window.history.replaceState(window.history.state, '', h)
  } else {
    if (window.location.hash === h) return
    window.history.pushState({ inApp: true }, '', h)
  }
  window.dispatchEvent(new HashChangeEvent('hashchange'))
}

export default function App() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [today, setToday] = useState(() => todayZurich())
  const [saved, setSaved] = useState(() => loadSaved())
  const [filters, setFilters] = useState({})
  const [toast, setToast] = useState('')
  const loadedAt = useRef(0)
  const lastBase = useRef(null)
  const route = useHashRoute()

  const load = useCallback(async () => {
    setError(null)
    try {
      const json = await fetchEvents()
      loadedAt.current = Date.now()
      setData(json)
      setToday(todayZurich())
    } catch (e) {
      setError(e)
    }
  }, [])

  useEffect(() => { load() }, [load])

  // Handy holt die App nach längerer Zeit wieder nach vorne: Datum und Daten auffrischen
  useEffect(() => {
    const on = () => {
      if (document.visibilityState !== 'visible') return
      setToday(todayZurich())
      if (loadedAt.current && Date.now() - loadedAt.current > RELOAD_AFTER_MS) load()
    }
    document.addEventListener('visibilitychange', on)
    return () => document.removeEventListener('visibilitychange', on)
  }, [load])

  useEffect(() => { storeSaved(saved) }, [saved])

  useEffect(() => {
    if (!toast) return undefined
    const t = setTimeout(() => setToast(''), 2600)
    return () => clearTimeout(t)
  }, [toast])

  // Daten aufbereiten: vergangene Events weg, Suchindex über alle Orte
  const prepared = useMemo(() => {
    if (!data) return null
    const byCity = {}
    const groups = new Map()
    for (const c of CITIES) {
      const list = (data.events[c.key] || [])
        .filter((e) => e && e.title && !isPast(e, today))
        .map((e) => ({ ...e, city: c.key, uid: e.uid || `${c.key}-${e.id}` }))
      byCity[c.key] = list
      for (const e of list) {
        const g = groups.get(e.uid) || { items: [], cities: [] }
        g.items.push(e)
        g.cities.push(e.city)
        groups.set(e.uid, g)
      }
    }
    const index = [...groups.values()].map(({ items, cities }) => ({
      e: items[0],
      cities,
      hay: haystack(items[0], [
        ...cities.map((k) => CITY_NAME[k]),
        ...items.slice(1).flatMap((x) => [x.loc, x.note]),
      ]),
    }))
    const nextKey = (e) => {
      const o = nextOccurrence(e, today)
      return o ? (o.start < today ? today : o.start) + (o.from || '') : '9999'
    }
    index.sort((a, b) => nextKey(a.e).localeCompare(nextKey(b.e)) || a.e.title.localeCompare(b.e.title))
    return { byCity, index, groups }
  }, [data, today])

  // Detailseite liegt über der letzten Liste (Scroll-Position bleibt erhalten)
  if (route.view !== 'detail') lastBase.current = route
  const base = route.view === 'detail' ? (lastBase.current || { view: 'city', city: route.city }) : route

  const go = navigate

  const openEvent = useCallback((e) => navigate({ view: 'detail', city: e.city, id: e.id }), [])

  const closeDetail = useCallback(() => {
    if (window.history.state && window.history.state.inApp) window.history.back()
    else navigate(lastBase.current || { view: 'city', city: route.city || 'ascona' }, { replace: true })
  }, [route.city])

  const toggleSaved = useCallback((uid) => {
    setSaved((s) => (s.includes(uid) ? s.filter((x) => x !== uid) : [...s, uid]))
  }, [])

  // beim Wechsel der Liste nach oben
  const baseKey = base.view + (base.city || '')
  useEffect(() => { window.scrollTo(0, 0) }, [baseKey])

  const counts = useMemo(() => {
    const o = {}
    for (const c of CITIES) o[c.key] = prepared ? prepared.byCity[c.key].length : null
    return o
  }, [prepared])

  let detailEvent = null
  if (route.view === 'detail' && prepared) {
    detailEvent = prepared.byCity[route.city].find((e) => e.id === route.id) || null
  }

  const title = base.view === 'search' ? 'Suche' : base.view === 'saved' ? 'Merkliste' : `Agenda ${CITY_NAME[base.city]}`

  return (
    <div className="app">
      <Header
        title={title}
        activeCity={base.view === 'city' ? base.city : null}
        counts={counts}
        savedCount={saved.length}
        onHome={() => go({ view: 'city', city: 'ascona' })}
        onCity={(city) => go({ view: 'city', city })}
        onSearch={() => go({ view: 'search', q: '' })}
        onSaved={() => go({ view: 'saved' })}
      />
      <main className="main">
        {!prepared && !error && <Loading />}
        {!prepared && error && <LoadError onRetry={load} />}
        {prepared && base.view === 'city' && (
          <CityView
            key={base.city}
            city={base.city}
            events={prepared.byCity[base.city]}
            today={today}
            filters={filters[base.city] || { range: 'alle', cat: 'alle' }}
            setFilters={(f) => setFilters((all) => ({ ...all, [base.city]: f }))}
            saved={saved}
            onOpen={openEvent}
          />
        )}
        {prepared && base.view === 'search' && (
          <SearchView
            index={prepared.index}
            today={today}
            query={base.q}
            setQuery={(q) => go({ view: 'search', q }, { replace: true })}
            onClose={() => go({ view: 'city', city: 'ascona' })}
            saved={saved}
            onOpen={openEvent}
          />
        )}
        {prepared && base.view === 'saved' && (
          <SavedView groups={prepared.groups} saved={saved} today={today} onOpen={openEvent} />
        )}
      </main>
      {prepared && <Footer updated={data.updated} updatedIso={data.updatedIso} />}
      {route.view === 'detail' && prepared && (
        <EventDetail
          event={detailEvent}
          cities={detailEvent ? prepared.groups.get(detailEvent.uid)?.cities || [detailEvent.city] : []}
          today={today}
          updated={data.updated}
          isSaved={detailEvent ? saved.includes(detailEvent.uid) : false}
          onToggleSaved={toggleSaved}
          onClose={closeDetail}
          onOtherCity={(city) => go({ view: 'detail', city, id: detailEvent.id }, { replace: true })}
          onToast={setToast}
        />
      )}
      <div className={`toast${toast ? ' show' : ''}`} role="status" aria-live="polite">{toast}</div>
    </div>
  )
}
