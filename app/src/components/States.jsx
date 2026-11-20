export function Loading() {
  return (
    <div className="list" aria-busy="true" aria-label="Events werden geladen">
      {[0, 1, 2, 3, 4].map((i) => (
        <div key={i} className="row skeleton" aria-hidden="true">
          <span className="thumb" />
          <span className="row-body">
            <span className="sk sk-short" />
            <span className="sk" />
            <span className="sk sk-mid" />
          </span>
        </div>
      ))}
    </div>
  )
}

export function LoadError({ onRetry }) {
  return (
    <div className="list">
      <div className="empty">
        <p>Die Events konnten gerade nicht geladen werden.</p>
        <p className="hint">Bitte Internetverbindung prüfen und nochmals versuchen.</p>
        <button type="button" className="cta" onClick={onRetry}>Nochmals versuchen</button>
      </div>
    </div>
  )
}
