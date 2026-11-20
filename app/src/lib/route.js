// Einfache Adressen im #-Teil der URL, damit jeder Link (auch auf ein einzelnes
// Event) auf GitHub Pages funktioniert:
//   #/ort/locarno          Agenda eines Ortes
//   #/e/locarno/10074      ein Event (Detailseite)
//   #/suche?q=winterland   Suche
//   #/merkliste            gemerkte Events

export const CITY_KEYS = ['ascona', 'locarno', 'minusio', 'tenero', 'orselina', 'muralto']

export function parseHash(hash) {
  const raw = String(hash || '').replace(/^#/, '')
  const [path, qs = ''] = raw.split('?')
  const parts = path.split('/').filter(Boolean).map((p) => {
    try { return decodeURIComponent(p) } catch { return p }
  })
  const params = new URLSearchParams(qs)
  if (parts[0] === 'e' && CITY_KEYS.includes(parts[1]) && parts[2]) {
    return { view: 'detail', city: parts[1], id: parts[2] }
  }
  if (parts[0] === 'ort' && CITY_KEYS.includes(parts[1])) return { view: 'city', city: parts[1] }
  if (parts[0] === 'suche') return { view: 'search', q: params.get('q') || '' }
  if (parts[0] === 'merkliste') return { view: 'saved' }
  return { view: 'city', city: 'ascona' }
}

export function hashFor(r) {
  switch (r.view) {
    case 'detail':
      return `#/e/${r.city}/${encodeURIComponent(r.id)}`
    case 'search':
      return r.q ? `#/suche?q=${encodeURIComponent(r.q)}` : '#/suche'
    case 'saved':
      return '#/merkliste'
    default:
      return `#/ort/${r.city || 'ascona'}`
  }
}
