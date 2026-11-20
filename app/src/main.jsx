import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

// Alte Offline-Speicher (Service Worker der ersten App-Version) entfernen,
// damit jedes Handy immer die aktuelle Version lädt.
if ('serviceWorker' in navigator && location.protocol.startsWith('http')) {
  navigator.serviceWorker.getRegistrations().then((rs) => rs.forEach((r) => r.unregister())).catch(() => {})
  if (window.caches) caches.keys().then((ks) => ks.forEach((k) => caches.delete(k))).catch(() => {})
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
