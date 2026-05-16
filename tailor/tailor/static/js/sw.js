// Tailor CRM Service Worker - Safe Offline Strategy

const CACHE_NAME = 'tailor-crm-v2';

// Only truly static assets go here
const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/manifest.json'
];

// -----------------------------
// INSTALL EVENT
// -----------------------------
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );

  // Activate immediately
  self.skipWaiting();
});

// -----------------------------
// ACTIVATE EVENT
// -----------------------------
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );

  self.clients.claim();
});

// -----------------------------
// FETCH EVENT
// -----------------------------
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only handle GET requests
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // ------------------------------------------------
  // 1. NEVER CACHE AUTH / SESSION ROUTES
  // ------------------------------------------------
  if (url.pathname.startsWith('/accounts/')) {
    event.respondWith(fetch(request));
    return;
  }

  // ------------------------------------------------
  // 2. BYPASS API / DYNAMIC BACKEND ROUTES
  // ------------------------------------------------
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/payments/') ||
    url.pathname.startsWith('/admin/')
  ) {
    event.respondWith(fetch(request));
    return;
  }

  // ------------------------------------------------
  // 3. HTML NAVIGATION STRATEGY
  // ------------------------------------------------
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          return caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, networkResponse.clone());
            return networkResponse;
          });
        })
        .catch(() => {
          // Offline fallback ONLY for UI pages
          return caches.match('/') || new Response('Offline', { status: 503 });
        })
    );
    return;
  }

  // ------------------------------------------------
  // 4. STATIC FILES (CSS/JS/IMAGES)
  // ------------------------------------------------
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request)
        .then((networkResponse) => {
          if (!networkResponse || networkResponse.status !== 200) {
            return networkResponse;
          }

          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, networkResponse.clone());
          });

          return networkResponse;
        })
        .catch(() => null);

      // Stale-while-revalidate
      return cachedResponse || fetchPromise;
    })
  );
});
