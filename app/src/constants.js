export const CITIES = [
  { key: 'ascona', name: 'Ascona', cover: 'ascona-cover.jpg' },
  { key: 'locarno', name: 'Locarno', cover: 'locarno-cover.jpg' },
  { key: 'minusio', name: 'Minusio', cover: 'minusio-cover.jpg' },
  { key: 'tenero', name: 'Tenero', cover: 'tenero-cover.jpg' },
  { key: 'orselina', name: 'Orselina', cover: 'orselina-cover.jpg' },
  { key: 'muralto', name: 'Muralto', cover: 'muralto-cover.jpg' },
]

export const CITY_NAME = Object.fromEntries(CITIES.map((c) => [c.key, c.name]))
export const COVER = Object.fromEntries(CITIES.map((c) => [c.key, c.cover]))

export const CATEGORIES = {
  weihnachten: { label: 'Weihnachten', icon: '🎄', color: '#b8322a' },
  silvester: { label: 'Silvester & Neujahr', icon: '🎆', color: '#5b3a9e' },
  fasnacht: { label: 'Fasnacht', icon: '🎊', color: '#d6336c' },
  august1: { label: '1. August', icon: '🇨🇭', color: '#d62828' },
  musik: { label: 'Musik', icon: '🎵', color: '#7b3fb8' },
  festival: { label: 'Festival', icon: '🎪', color: '#e8743b' },
  kultur: { label: 'Kultur', icon: '🎭', color: '#a83279' },
  tradition: { label: 'Tradition', icon: '🎉', color: '#a04000' },
  ausstellung: { label: 'Ausstellung', icon: '🖼️', color: '#2471a3' },
  sport: { label: 'Sport', icon: '🏃', color: '#1e8449' },
  kulinarik: { label: 'Kulinarik', icon: '🍷', color: '#b9770e' },
  fuehrung: { label: 'Führung', icon: '🧭', color: '#16859e' },
  natur: { label: 'Natur', icon: '🌿', color: '#27ae60' },
  markt: { label: 'Markt', icon: '🛍️', color: '#16a085' },
  kino: { label: 'Kino', icon: '🎬', color: '#8e44ad' },
  wellness: { label: 'Wellness', icon: '🧘', color: '#0e9aa7' },
  kinder: { label: 'Kinder', icon: '🧸', color: '#e67e22' },
  kurs: { label: 'Kurs', icon: '🎓', color: '#2c7be5' },
  event: { label: 'Event', icon: '📅', color: '#5d6d7e' },
}

export function catInfo(key) {
  return CATEGORIES[key] || CATEGORIES.event
}

export const RANGES = [
  { key: 'alle', label: 'Alle Daten' },
  { key: 'heute', label: 'Heute' },
  { key: 'wochenende', label: 'Wochenende' },
  { key: '7', label: '7 Tage' },
  { key: '30', label: '30 Tage' },
]

export const SEARCH_SUGGESTIONS = ['Winterland', 'Weihnachtsmarkt', 'Eisbahn', 'Konzert', 'Silvester', 'Kinder', 'Ausstellung']

export const APP_URL = 'https://kipferdp.github.io/eventi-lago-maggiore/'
