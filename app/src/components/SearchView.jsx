import { useEffect, useMemo, useRef, useState } from 'react'
import { SEARCH_SUGGESTIONS } from '../constants.js'
import { matches, normalize } from '../lib/search.js'
import { EventRow } from './EventRow.jsx'

export default function SearchView({ index, today, query, setQuery, onClose, saved, onOpen }) {
  const [text, setText] = useState(query || '')
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  // Adresse (#/suche?q=…) leicht verzögert nachführen, damit man den Link teilen kann
  useEffect(() => {
    const t = setTimeout(() => { if (text !== query) setQuery(text) }, 350)
    return () => clearTimeout(t)
  }, [text]) // eslint-disable-line react-hooks/exhaustive-deps

  // Treffer: zuerst Titel-Treffer und Highlights, sonst nach Datum (Index ist schon nach Datum sortiert)
  const results = useMemo(() => {
    const q = text.trim()
    if (!q) return []
    const nq = normalize(q)
    const score = (x) => (normalize(x.e.title).includes(nq) ? 2 : 0) + (x.e.isTop ? 1 : 0)
    return index
      .filter((x) => matches(x.hay, q))
      .map((x, i) => ({ x, i, s: score(x) }))
      .sort((a, b) => b.s - a.s || a.i - b.i)
      .map((r) => r.x)
  }, [index, text])

  const savedSet = new Set(saved)
  const q = text.trim()

  return (
    <div className="list">
      <form className="searchbar" role="search" onSubmit={(ev) => { ev.preventDefault(); inputRef.current?.blur() }}>
        <input
          ref={inputRef}
          type="search"
          value={text}
          onChange={(ev) => setText(ev.target.value)}
          placeholder="Alle Orte durchsuchen, z. B. Winterland"
          aria-label="Suchbegriff"
          enterKeyHint="search"
          autoComplete="off"
        />
        <button type="button" className="link-btn" onClick={onClose}>Abbrechen</button>
      </form>

      {!q && (
        <div className="suggest">
          <p>Vorschläge:</p>
          <div className="chips wrap">
            {SEARCH_SUGGESTIONS.map((s) => (
              <button type="button" key={s} className="fchip" onClick={() => setText(s)}>{s}</button>
            ))}
          </div>
          <p className="hint">Gesucht wird in Titel, Beschreibung, Ort und Kategorie aller sechs Orte. Kleine Tippfehler sind kein Problem.</p>
        </div>
      )}

      {q && (
        <p className="result-count" role="status">
          {results.length === 0 ? 'Keine Treffer.' : `${results.length} Treffer`}
        </p>
      )}
      {q && results.length === 0 && (
        <p className="hint">Tipp: kürzeres Wort versuchen (z. B. «Weihnacht» statt «Weihnachtsmärkte») oder einen Vorschlag antippen.</p>
      )}

      {results.map(({ e, cities }) => (
        <EventRow key={e.uid} e={e} today={today} cities={cities} saved={savedSet.has(e.uid)} onOpen={onOpen} />
      ))}
    </div>
  )
}
