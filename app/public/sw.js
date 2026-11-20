// KILL-SWITCH Service Worker
// Entfernt den alten (hartnäckigen) Offline-Speicher von allen Geräten.
// Danach lädt die App immer direkt die aktuelle Version von GitHub Pages.
self.addEventListener('install', e => self.skipWaiting());

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    // alle Caches löschen
    const keys = await caches.keys();
    await Promise.all(keys.map(k => caches.delete(k)));
    // sich selbst abmelden
    await self.registration.unregister();
    // offene Seiten neu laden -> holt frische Version
    const clients = await self.clients.matchAll({ type: 'window' });
    for (const c of clients) {
      try { c.navigate(c.url); } catch (_) {}
    }
  })());
});

// Während der Kill-Switch aktiv ist: nichts mehr aus dem Cache liefern,
// alles direkt aus dem Netz holen.
self.addEventListener('fetch', e => {
  e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
});
