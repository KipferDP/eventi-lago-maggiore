import { nextOccurrence } from '../lib/dates.js'
import { EventRow } from './EventRow.jsx'

export default function SavedView({ groups, saved, today, onOpen }) {
  const list = saved
    .map((uid) => groups.get(uid))
    .filter(Boolean)
    .map((g) => ({ e: g.items[0], cities: g.cities, o: nextOccurrence(g.items[0], today) }))
    .filter((x) => x.o)
    .sort((a, b) => (a.o.start < today ? today : a.o.start).localeCompare(b.o.start < today ? today : b.o.start))

  return (
    <div className="list">
      {list.length === 0 ? (
        <div className="empty">
          <p>Noch nichts gemerkt.</p>
          <p className="hint">Bei einem Event auf «♡ Merken» tippen. Die Merkliste bleibt nur auf diesem Gerät gespeichert.</p>
        </div>
      ) : (
        <>
          <p className="hint">Nur auf diesem Gerät gespeichert. Vorbei = verschwindet automatisch.</p>
          {list.map(({ e, cities }) => (
            <EventRow key={e.uid} e={e} today={today} cities={cities} saved onOpen={onOpen} />
          ))}
        </>
      )}
    </div>
  )
}
