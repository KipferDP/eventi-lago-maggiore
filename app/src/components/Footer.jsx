import { useState } from 'react'

function ageDays(iso) {
  const t = Date.parse(iso || '')
  return Number.isFinite(t) ? (Date.now() - t) / 86400000 : 0
}

export default function Footer({ updated, updatedIso }) {
  const [open, setOpen] = useState(false)
  const old = ageDays(updatedIso) > 3
  return (
    <footer className="foot">
      <p className={old ? 'stale' : ''}>
        Daten: Ticino Turismo (offiziell) + eigene Ergänzungen{updated ? ` · Stand ${updated}` : ''}
      </p>
      <p>Gratis und ohne Anmeldung – einfach den Link teilen.</p>
      <button type="button" className="link-btn" onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        📲 So kommt die App aufs Handy
      </button>
      {open && (
        <div className="install">
          <p><b>iPhone:</b> Link in Safari öffnen → unten auf Teilen (Viereck mit Pfeil) → «Zum Home-Bildschirm» → Hinzufügen.</p>
          <p><b>Android:</b> Link in Chrome öffnen → oben rechts ⋮ → «Zum Startbildschirm hinzufügen».</p>
        </div>
      )}
    </footer>
  )
}
