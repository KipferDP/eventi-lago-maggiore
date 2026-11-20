import { useEffect, useRef } from 'react'
import { CITIES } from '../constants.js'

export default function Header({ title, activeCity, counts, savedCount, onHome, onCity, onSearch, onSaved }) {
  const tabsRef = useRef(null)

  // aktiven Ort in der Tab-Leiste sichtbar halten (Orselina/Muralto auf kleinen Handys)
  useEffect(() => {
    const el = tabsRef.current?.querySelector('.tab.active')
    if (el && el.scrollIntoView) el.scrollIntoView({ block: 'nearest', inline: 'center' })
  }, [activeCity])

  return (
    <header className="hdr">
      <div className="hdr-top">
        <button type="button" className="brand" onClick={onHome} title="Zur Startseite (Ascona)">
          <span aria-hidden="true">🏠</span> Eventi · Lago Maggiore
        </button>
        <div className="hdr-actions">
          <button type="button" className="round" onClick={onSaved} aria-label={`Merkliste (${savedCount})`} title="Merkliste">
            <span aria-hidden="true">♥</span>
            {savedCount > 0 && <span className="dot">{savedCount}</span>}
          </button>
          <button type="button" className="round" onClick={onSearch} aria-label="Alle Events durchsuchen" title="Suchen">
            <span aria-hidden="true">🔍</span>
          </button>
        </div>
      </div>
      <h1>{title}</h1>
      <nav className="tabs" ref={tabsRef} aria-label="Orte">
        {CITIES.map((c) => (
          <button
            type="button"
            key={c.key}
            className={`tab${activeCity === c.key ? ' active' : ''}`}
            aria-current={activeCity === c.key ? 'page' : undefined}
            onClick={() => onCity(c.key)}
          >
            {c.name} {counts[c.key] != null && <span className="count">{counts[c.key]}</span>}
          </button>
        ))}
      </nav>
    </header>
  )
}
