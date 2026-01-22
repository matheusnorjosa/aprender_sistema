/**
 * AS v2 - Service Worker (Issue #416)
 *
 * Provides offline support with cache-first for static assets
 * and network-first with cache fallback for API requests.
 */

const CACHE_VERSION = 'v1';
const STATIC_CACHE_NAME = `aprender-v2-static-${CACHE_VERSION}`;
const API_CACHE_NAME = `aprender-v2-api-${CACHE_VERSION}`;

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/logo.svg',
  '/manifest.json',
];

// API routes that can be cached for offline use
const CACHEABLE_API_ROUTES = [
  '/api/v1/options/',
  '/api/v1/me/',
  '/api/v1/config/',
];

// Install: cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  // Activate immediately without waiting for existing clients
  self.skipWaiting();
});

// Activate: clean old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => {
            // Delete old versions of our caches
            return (
              (name.startsWith('aprender-v2-static-') && name !== STATIC_CACHE_NAME) ||
              (name.startsWith('aprender-v2-api-') && name !== API_CACHE_NAME)
            );
          })
          .map((name) => {
            console.log('[SW] Deleting old cache:', name);
            return caches.delete(name);
          })
      );
    })
  );
  // Take control of all clients immediately
  self.clients.claim();
});

// Fetch: handle requests
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-HTTP requests
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // API requests: network-first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithCache(request));
    return;
  }

  // Static assets: cache-first with network fallback
  event.respondWith(cacheFirstWithNetwork(request));
});

/**
 * Network-first strategy with cache fallback for API requests.
 */
async function networkFirstWithCache(request) {
  try {
    const response = await fetch(request);

    // Cache successful GET requests for cacheable routes
    if (request.method === 'GET' && response.ok && isCacheableApiRoute(request.url)) {
      const cache = await caches.open(API_CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);

    // Try cache
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }

    // Return offline JSON response for API requests
    return new Response(
      JSON.stringify({
        error: {
          code: 'OFFLINE',
          message: 'Voce esta offline. Verifique sua conexao.',
        },
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}

/**
 * Cache-first strategy with network fallback for static assets.
 */
async function cacheFirstWithNetwork(request) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);

    // Cache successful responses
    if (response.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.log('[SW] Network failed, returning offline page');

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }

    // Return empty response for other requests
    return new Response('', { status: 503 });
  }
}

/**
 * Check if URL is a cacheable API route.
 */
function isCacheableApiRoute(url) {
  return CACHEABLE_API_ROUTES.some((route) => url.includes(route));
}

// Handle messages from clients
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
