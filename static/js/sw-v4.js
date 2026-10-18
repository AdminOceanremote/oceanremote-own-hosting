// We increment this to V4 to force the browser to recognize a change
const CACHE_NAME = 'oceamic-v2026-03-v4';
const PRECACHE_URLS = [
    '/',
    '/static/css/style.css',
    '/static/js/notifications.js',
    '/static/images/pic2.png',
    '/static/audio/notification.mp3'
];

console.log("Oceamic Master SW VERSION 4 Loaded"); // If you don't see this in F12, it's not working

// 1. INSTALL
self.addEventListener('install', event => {
    self.skipWaiting(); // Force the new worker to take over immediately
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    );
});

// 2. ACTIVATE
self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            self.clients.claim(), // Take control of all open tabs immediately
            caches.keys().then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cacheName => {
                        if (cacheName !== CACHE_NAME) {
                            return caches.delete(cacheName);
                        }
                    })
                );
            })
        ])
    );
});

// 3. PUSH: The "Absolute" Enforcer
self.addEventListener('push', function(event) {
    let data = {};
    
    // Attempt to parse the data safely
    if (event.data) {
        try {
            data = event.data.json();
            console.log("Push Data Received:", data);
        } catch (e) {
            data = { body: event.data.text() };
            console.log("Push Text Received:", data.body);
        }
    }

    // THE FIX: Hard-code the title variable directly. 
    // Do NOT trust the server to provide 'title' or 'head' right now.
    const forcedTitle = "Oceamic II Alert";
    
    // Check every possible key to find a message. If all fail, use the fallback.
    const message = data.body || data.message || data.head || "New sensor update for ChartG.";

    const options = {
        body: message,
        icon: "/static/images/pic2.png",
        badge: "/static/images/pic2.png",
        vibrate: [200, 100, 200],
        data: {
            url: data.url || "/"
        }
    };

    event.waitUntil(
        self.registration.showNotification(forcedTitle, options)
    );
});

// 4. CLICK
self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const targetUrl = event.notification.data.url || "/";
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(windowClients => {
            for (let client of windowClients) {
                if (client.url === targetUrl && 'focus' in client) return client.focus();
            }
            if (clients.openWindow) return clients.openWindow(targetUrl);
        })
    );
});

// 5. FETCH
self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;
    event.respondWith(
        fetch(event.request).catch(() => caches.match(event.request))
    );
});