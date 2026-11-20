import { test } from 'node:test'
import assert from 'node:assert/strict'
import { normalize, haystack, matches } from './search.js'
import { buildIcs, fold } from './ics.js'
import { parseHash, hashFor } from './route.js'

const winterland = {
  uid: 'ticino-10074', id: '10074', title: 'Winterland 2026/27', loc: 'Piazza Grande, Locarno',
  catLabel: 'Weihnachten', keywords: 'Weihnachten Advent Winterwunderland Eisbahn',
  desc: ['In Ascona ist eine der wichtigsten Neuerungen … ein elegantes Winterwunderland …'],
  start: '2026-11-19', end: '2027-01-06',
  dates: [{ start: '2026-11-19', end: '2027-01-06', from: '10:00', to: '02:00' }],
}

test('normalize entfernt Akzente und Umlaute', () => {
  assert.equal(normalize('Märkte À Noël, Straße!'), 'markte a noel strasse')
})

test('Suche findet Winterwunderland über Beschreibung und Stichwörter', () => {
  const hay = haystack(winterland, ['Ascona', 'Locarno'])
  assert.equal(matches(hay, 'Winterwunderland'), true)
  assert.equal(matches(hay, 'winterland ascona'), true)
  assert.equal(matches(hay, 'Eisbahn'), true)
  assert.equal(matches(hay, 'Weinachten'), true) // Tippfehler
  assert.equal(matches(hay, 'Jazz'), false)
  assert.equal(matches(hay, ''), true)
})

test('Kalender-Datei: ganztägig über mehrere Tage', () => {
  const ics = buildIcs({ ...winterland, dates: [{ start: '2026-11-19', end: '2027-01-06', from: '10:00', to: '02:00' }] },
    { url: 'https://example.org/#/e/locarno/10074', now: new Date('2026-11-20T08:00:00Z') })
  assert.match(ics, /DTSTART;VALUE=DATE:20261119/)
  assert.match(ics, /DTEND;VALUE=DATE:20270107/)
  assert.match(ics, /SUMMARY:Winterland 2026\/27/)
  assert.ok(ics.endsWith('END:VCALENDAR\r\n'))
})

test('Kalender-Datei: Abend mit Ende nach Mitternacht', () => {
  const ics = buildIcs({ id: 'x', title: 'Konzert; Test', loc: 'Teatro, Locarno',
    dates: [{ start: '2026-11-20', end: '2026-11-20', from: '21:00', to: '01:30' }] }, { now: new Date('2026-11-20T08:00:00Z') })
  assert.match(ics, /DTSTART;TZID=Europe\/Zurich:20261120T210000/)
  assert.match(ics, /DTEND;TZID=Europe\/Zurich:20261121T013000/)
  assert.match(ics, /SUMMARY:Konzert\\; Test/)
  assert.match(ics, /BEGIN:VTIMEZONE/)
})

test('Zeilen falten nach Byte, Umlaute bleiben ganz', () => {
  const long = 'DESCRIPTION:' + 'ä'.repeat(100)
  const folded = fold(long).split('\r\n')
  const enc = new TextEncoder()
  folded.forEach((l) => assert.ok(enc.encode(l).length <= 75))
  assert.equal(folded.map((l, i) => (i ? l.slice(1) : l)).join(''), long)
})

test('Adressen (#-Links) hin und zurück', () => {
  assert.deepEqual(parseHash('#/e/locarno/10074'), { view: 'detail', city: 'locarno', id: '10074' })
  assert.deepEqual(parseHash('#/ort/ascona'), { view: 'city', city: 'ascona' })
  assert.deepEqual(parseHash('#/suche?q=winter%20land'), { view: 'search', q: 'winter land' })
  assert.deepEqual(parseHash(''), { view: 'city', city: 'ascona' })
  assert.deepEqual(parseHash('#/ort/zuerich'), { view: 'city', city: 'ascona' })
  assert.equal(hashFor({ view: 'search', q: 'a b' }), '#/suche?q=a%20b')
})
