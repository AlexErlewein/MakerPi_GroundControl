// ─── MakerPi GroundControl Service Worker ───────────────────────
// Version: bump this to invalidate all caches on deploy
const SW_VERSION = 'gc-v7';

// Cache names
const CACHE_STATIC  = `${SW_VERSION}-static`;
const CACHE_PAGES   = `${SW_VERSION}-pages`;
const CACHE_API     = `${SW_VERSION}-api`;

// Static assets to pre-cache on install
const PRECACHE_URLS = [
    '/static/css/style.css',
    '/static/js/theme.js',
    '/static/js/pwa.js',
    '/graphics/H3ckeLogo.svg',
    '/static/manifest.json',
    '/offline.html',
];

// API routes that should use stale-while-revalidate (data that changes rarely)
const SWR_PATTERNS = [
    '/api/mitglieder',
    '/api/tags',
    '/api/buchhaltung',
    '/api/payment/config',
    '/api/database/stats',
];

// API routes that are real-time / should always fetch fresh
const NETWORK_ONLY_PATTERNS = [
    '/api/dashboard/',
    '/api/status',
    '/api/scans',
    '/api/auth/',
    '/api/laufzettel/',
    '/api/guest/',
    '/api/kasse/',
    '/api/write-result',
    // Sub-resources of SWR-cached list endpoints must always be fresh
    // (e.g. /api/mitglieder/5/permissions) so mutations are reflected immediately
    '/api/mitglieder/',
    '/api/tags/',
];

// ─── Install: pre-cache critical assets ─────────────────────────
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_STATIC).then((cache) => {
            return cache.addAll(PRECACHE_URLS);
        }).then(() => self.skipWaiting())
    );
});

// ─── Activate: clean up old caches ──────────────────────────────
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((key) => key.startsWith('gc-') && key !== CACHE_STATIC && key !== CACHE_PAGES && key !== CACHE_API)
                    .map((key) => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// ─── Fetch: routing strategy ────────────────────────────────────
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Only handle same-origin requests
    if (url.origin !== location.origin) return;

    // Skip non-GET requests (mutations go straight to network)
    if (request.method !== 'GET') {
        // Queue mutations for background sync if offline
        if ('sync' in self.registration) {
            event.respondWith(
                fetch(request).catch(() => {
                    return queueForSync(request);
                })
            );
        }
        return;
    }

    // Skip SSE streams
    if (url.pathname.includes('/stream')) return;

    // Route to appropriate strategy
    if (isStaticAsset(url.pathname)) {
        event.respondWith(cacheFirst(request));
    } else if (isNetworkOnlyApi(url.pathname)) {
        event.respondWith(networkOnly(request));
    } else if (isSwrApi(url.pathname)) {
        event.respondWith(staleWhileRevalidate(request, CACHE_API));
    } else if (isApiCall(url.pathname)) {
        event.respondWith(networkFirst(request, CACHE_API));
    } else {
        // HTML pages: network-first with offline fallback
        event.respondWith(networkFirst(request, CACHE_PAGES));
    }
});

// ─── Background Sync ────────────────────────────────────────────
self.addEventListener('sync', (event) => {
    if (event.tag === 'gc-pending-mutations') {
        event.waitUntil(replayPendingMutations());
    }
});

// ─── Push Notifications ─────────────────────────────────────────
self.addEventListener('push', (event) => {
    if (!event.data) return;

    try {
        const data = event.data.json();
        const options = {
            body: data.body || '',
            icon: '/graphics/H3ckeLogo.svg',
            badge: '/graphics/H3ckeLogo.svg',
            tag: data.tag || 'gc-notification',
            data: data.data || {},
            vibrate: data.vibrate || [100, 50, 100],
            actions: data.actions || [],
        };

        event.waitUntil(
            self.registration.showNotification(data.title || 'GroundControl', options)
        );
    } catch (e) {
        console.error('[SW] Push notification error:', e);
    }
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();

    const urlToOpen = event.notification.data?.url || '/dashboard';

    event.waitUntil(
        self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
            // Focus existing window if open
            for (const client of clients) {
                if (client.url.includes(urlToOpen) && 'focus' in client) {
                    return client.focus();
                }
            }
            // Otherwise open new window
            return self.clients.openWindow(urlToOpen);
        })
    );
});

// ─── Strategy implementations ───────────────────────────────────

async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_STATIC);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Offline', { status: 503, statusText: 'Offline' });
    }
}

async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;

        // For HTML navigation requests, show offline page
        if (request.headers.get('Accept')?.includes('text/html')) {
            const offline = await caches.match('/offline.html');
            if (offline) return offline;
        }

        return new Response(JSON.stringify({ error: 'Offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        });
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);

    const fetchPromise = fetch(request).then((response) => {
        if (response.ok) {
            cache.put(request, response.clone());
        }
        return response;
    }).catch(() => cached);

    return cached || fetchPromise;
}

async function networkOnly(request) {
    try {
        return await fetch(request);
    } catch {
        return new Response(JSON.stringify({ error: 'Offline' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
        });
    }
}

// ─── Route matching helpers ─────────────────────────────────────

function isStaticAsset(pathname) {
    return pathname.match(/\.(css|js|svg|png|jpg|jpeg|gif|ico|woff2?|ttf|eot)$/i);
}

function isApiCall(pathname) {
    return pathname.startsWith('/api/');
}

function isNetworkOnlyApi(pathname) {
    return NETWORK_ONLY_PATTERNS.some((p) => pathname.startsWith(p));
}

function isSwrApi(pathname) {
    return SWR_PATTERNS.some((p) => pathname.startsWith(p));
}

// ─── Background sync queue (IndexedDB) ──────────────────────────

async function queueForSync(request) {
    const db = await openSyncDB();
    const tx = db.transaction('pending', 'readwrite');
    const store = tx.objectStore('pending');

    const body = await request.text();
    await store.add({
        url: request.url,
        method: request.method,
        headers: Object.fromEntries(request.headers.entries()),
        body: body,
        timestamp: Date.now(),
    });

    // Register for sync when back online
    await self.registration.sync.register('gc-pending-mutations');

    return new Response(JSON.stringify({ queued: true }), {
        status: 202,
        headers: { 'Content-Type': 'application/json' },
    });
}

async function replayPendingMutations() {
    const db = await openSyncDB();
    const tx = db.transaction('pending', 'readwrite');
    const store = tx.objectStore('pending');
    const all = await store.getAll();

    for (const entry of all) {
        try {
            await fetch(entry.url, {
                method: entry.method,
                headers: entry.headers,
                body: entry.body || undefined,
            });
            // Remove from queue on success
            store.delete(entry.id);
        } catch {
            // Leave in queue for next sync attempt
        }
    }
}

function openSyncDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('gc-sync-db', 1);
        request.onupgradeneeded = () => {
            const db = request.result;
            if (!db.objectStoreNames.contains('pending')) {
                db.createObjectStore('pending', { keyPath: 'id', autoIncrement: true });
            }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}
