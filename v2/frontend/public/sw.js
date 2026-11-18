/**
 * AS v2 - Service Worker (Issue #416)
 *
 * Provides offline support with cache-first for static assets.
 *
 * SEG-54: resposta de API NUNCA é guardada nem servida do cache. As listas de /api/options/ e
 * /api/config/ mudam conforme quem está logado, e o cache não é separado por pessoa: em computador
 * compartilhado, quem entrava depois recebia, sem rede, as listas da pessoa anterior. Chamada de API
 * vai sempre à rede; sem rede, devolve o JSON OFFLINE (503).
 */

const CACHE_VERSION = 'v5';
const STATIC_CACHE_NAME = `aprender-v2-static-${CACHE_VERSION}`;
// Prefixo dos caches de API de versões antigas (até a v4); apagados ao ativar. Espelhado em
// src/services/swCache.ts, que os apaga também no logout.
const API_CACHE_PREFIX = 'aprender-v2-api-';

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/offline.html',
  '/logo.svg',
  '/manifest.json',
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
            // Delete old versions of the static cache and every API cache (SEG-54)
            return (
              (name.startsWith('aprender-v2-static-') && name !== STATIC_CACHE_NAME) ||
              name.startsWith(API_CACHE_PREFIX)
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

  // Django admin: o service worker não toca (SEG-54). O cache-first abaixo guardaria para sempre o JSON
  // do autocomplete do admin (nomes de pessoas) no cache estático, que o logout não apaga.
  if (url.pathname.startsWith('/admin/')) {
    return;
  }

  // API requests: network only, never cached (SEG-54)
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkOnly(request, { usarCache: false }));
    return;
  }

  // Navigation requests (HTML pages): network-first to always get latest index.html
  if (request.mode === 'navigate') {
    event.respondWith(networkOnly(request, { usarCache: true }));
    return;
  }

  // Static assets (JS, CSS, images): cache-first with network fallback
  event.respondWith(cacheFirstWithNetwork(request));
});

/**
 * Network strategy for API and navigation requests: nothing is written to the cache here.
 * `usarCache` (navigation only): on network failure, serve the precached page if there is one.
 * API requests never read the cache (SEG-54).
 */
async function networkOnly(request, { usarCache }) {
  try {
    return await fetch(request);
  } catch {
    console.log('[SW] Network failed:', request.url);

    if (usarCache) {
      const cached = await caches.match(request);
      if (cached) {
        return cached;
      }
    }

    // DEF-27: abrir uma página sem conexão mostra a página amigável, não o JSON da API.
    if (request.mode === 'navigate') {
      const paginaOffline = await caches.match('/offline.html');
      if (paginaOffline) {
        return paginaOffline;
      }
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
  } catch {
    console.log('[SW] Network failed, returning offline page');

    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/offline.html');
    }

    // Return empty response for other requests
    return new Response('', { status: 503 });
  }
}

// Handle messages from clients
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});
