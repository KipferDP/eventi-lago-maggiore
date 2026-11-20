// Suche: unabhängig von Gross/Klein, Akzenten und Umlauten, verträgt kleine Tippfehler.

export function normalize(s) {
  return String(s || '')
    .toLowerCase()
    .replace(/ß/g, 'ss')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

/** Alle durchsuchbaren Texte eines Events (inkl. Beschreibung und Suchwörter). */
export function haystack(e, extra = []) {
  const parts = [
    e.title, e.summary, e.loc, e.catLabel, e.parent, e.keywords, e.organizer, e.note,
    ...(e.desc || []), ...extra,
  ]
  return normalize(parts.filter(Boolean).join(' '))
}

// Levenshtein mit Abbruch, sobald die Grenze überschritten ist.
function editDistance(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1
  let prev = Array.from({ length: b.length + 1 }, (_, i) => i)
  for (let i = 1; i <= a.length; i++) {
    const cur = [i]
    let rowMin = i
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
      if (cur[j] < rowMin) rowMin = cur[j]
    }
    if (rowMin > max) return max + 1
    prev = cur
  }
  return prev[b.length]
}

function tokenMatches(token, hay, words) {
  if (hay.includes(token)) return true
  if (token.length < 5) return false
  const max = token.length >= 9 ? 2 : 1
  return words.some((w) => w.length >= 4 && editDistance(token, w, max) <= max)
}

/** true, wenn jedes Suchwort (oder eine leicht vertippte Form davon) vorkommt. */
export function matches(hay, query) {
  const tokens = normalize(query).split(' ').filter(Boolean)
  if (!tokens.length) return true
  let words = null
  return tokens.every((t) => {
    if (hay.includes(t)) return true
    if (!words) words = Array.from(new Set(hay.split(' ')))
    return tokenMatches(t, hay, words)
  })
}
