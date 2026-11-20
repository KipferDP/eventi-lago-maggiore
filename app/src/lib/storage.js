// Merkliste: bleibt nur auf diesem Gerät gespeichert (localStorage), nichts geht ins Internet.
const KEY = 'eventi.merkliste.v1'

export function loadSaved() {
  try {
    const arr = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(arr) ? arr.filter((x) => typeof x === 'string') : []
  } catch {
    return []
  }
}

export function storeSaved(list) {
  try {
    localStorage.setItem(KEY, JSON.stringify(list))
  } catch {
    /* Privatmodus o. ä.: Merkliste gilt dann nur bis zum Schliessen */
  }
}
