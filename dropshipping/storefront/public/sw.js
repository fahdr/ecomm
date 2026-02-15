/**
 * Service Worker for Dropshipping Storefront PWA.
 *
 * Implements a stale-while-revalidate caching strategy for static assets
 * and a network-first strategy for API calls. This ensures the storefront
 * loads quickly even on slow or offline connections while keeping data fresh.
 *
 * **For Developers:**
 *   Update CACHE_VERSION when deploying new assets to bust the cache.
 *   The SW caches all same-origin requests except API calls and Chrome extensions.
 *
 * **For QA Engineers:**
 *   Test offline mode by toggling "Offline" in DevTools > Application > Service Workers.
 *   Verify that previously visited pages load from cache and that API errors show
 *   a user-friendly fallback.
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `dynamic-${CACHE_VERSION}`;

const PRECACHE_URLS = [
  '/',
  '/offline',
];

// Install: precache critical assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== STATIC_CACHE && key !== DYNAMIC_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// Fetch: network-first for API, stale-while-revalidate for assets
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests and cross-origin
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  // API calls: network first, cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const cloned = response.clone();
          caches.open(DYNAMIC_CACHE).then((cache) => cache.put(request, cloned));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets: stale-while-revalidate
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetched = fetch(request).then((response) => {
        const cloned = response.clone();
        caches.open(STATIC_CACHE).then((cache) => cache.put(request, cloned));
        return response;
      });
      return cached || fetched;
    })
  );
});
