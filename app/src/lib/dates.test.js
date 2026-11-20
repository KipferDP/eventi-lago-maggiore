import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  todayZurich, addDays, dayLabel, rangeFor, isPast, isOngoing, overlaps, cardDate, moreDates, fmtShort,
} from './dates.js'

test('todayZurich nutzt Schweizer Zeit', () => {
  // 23:30 UTC am 19.11. = 00:30 am 20.11. in Zürich (Winterzeit +1)
  assert.equal(todayZurich(new Date('2026-11-19T23:30:00Z')), '2026-11-20')
  assert.equal(todayZurich(new Date('2026-11-19T22:30:00Z')), '2026-11-19')
})

test('addDays über Monats- und Jahresgrenze', () => {
  assert.equal(addDays('2026-12-31', 1), '2027-01-01')
  assert.equal(addDays('2026-03-01', -1), '2026-02-28')
})

test('Wochentag und Tageslabel', () => {
  assert.equal(fmtShort('2026-11-20'), 'Fr, 20.11.')
  assert.equal(dayLabel('2026-11-20', '2026-11-20'), 'Heute')
  assert.equal(dayLabel('2026-11-21', '2026-11-20'), 'Morgen')
  assert.equal(dayLabel('2026-11-22', '2026-11-20'), 'So, 22.11.')
})

test('Wochenende = Freitag bis Sonntag', () => {
  assert.deepEqual(rangeFor('wochenende', '2026-11-18'), ['2026-11-20', '2026-11-22']) // Mi
  assert.deepEqual(rangeFor('wochenende', '2026-11-20'), ['2026-11-20', '2026-11-22']) // Fr
  assert.deepEqual(rangeFor('wochenende', '2026-11-21'), ['2026-11-21', '2026-11-22']) // Sa
  assert.deepEqual(rangeFor('wochenende', '2026-11-22'), ['2026-11-22', '2026-11-22']) // So
  assert.equal(rangeFor('alle', '2026-11-20'), null)
})

const winterland = { start: '2026-11-19', end: '2027-01-06', dates: [{ start: '2026-11-19', end: '2027-01-06', from: '10:00', to: '02:00' }] }
const brecht = { start: '2026-11-21', end: '2026-11-22', dates: [
  { start: '2026-11-21', end: '2026-11-21', from: '20:30', to: '20:30' },
  { start: '2026-11-22', end: '2026-11-22', from: '17:00', to: '17:00' },
] }

test('laufend, vorbei, Überschneidung', () => {
  assert.equal(isOngoing(winterland, '2026-11-20'), true)
  assert.equal(isOngoing(winterland, '2026-11-19'), false) // beginnt heute
  assert.equal(isPast(winterland, '2027-01-07'), true)
  assert.equal(isPast({ start: '2026-11-19', end: '2026-11-19' }, '2026-11-20'), true)
  assert.equal(overlaps(brecht, '2026-11-22', '2026-11-22'), true)
  assert.equal(overlaps(brecht, '2026-11-23', '2026-11-30'), false)
})

test('Kartendatum zeigt den nächsten Termin', () => {
  assert.equal(cardDate(winterland, '2026-11-20'), 'bis 06.01.2027')
  assert.equal(cardDate(brecht, '2026-11-20'), 'Sa, 21.11. · 20:30 Uhr')
  assert.equal(cardDate(brecht, '2026-11-22'), 'So, 22.11. · 17:00 Uhr')
  assert.equal(moreDates(brecht, '2026-11-20'), 1)
  assert.equal(moreDates(brecht, '2026-11-22'), 0)
})
