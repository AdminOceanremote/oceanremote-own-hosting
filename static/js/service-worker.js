// We use V5 to force the browser to dump all old "undefined" memory
const CACHE_NAME = 'oceanremote-v2026-v5';
const PRECACHE_URLS = [
    '/',
    '/static/css/style.css',
    '/static/js/notifications.js',
    '/static/images/pic2.png',
    '/static/audio/notification.mp3'
];

console.log("OceanRemote Master SW V5 Active");

self.addEventListener('install', event => {
    self.skipWaiting(); 
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        Promise.all([
            self.clients.claim(),
            caches.keys().then(keys => Promise.all(
                keys.map(key => key !== CACHE_NAME ? caches.delete(key) : null)
            ))
        ])
    );
});

self.addEventListener('push', function(event) {
    let data = {};
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data = { body: event.data.text() };
        }
    }

    // THE FIX: Hard-code this so "undefined" is physically impossible
    const forcedTitle = "OceanRemote Alert";
    
    // Check all possible fields for the message body
    const message = data.body || data.message || data.head || "Environmental Update";

    const options = {
        body: message,
        icon: "/static/images/pic2.png",
        badge: "/static/images/pic2.png",
        vibrate: [200, 100, 200],
        data: {
            url: data.url || "/"
        }
    };

    event.waitUntil(self.registration.showNotification(forcedTitle, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const targetUrl = event.notification.data.url || "/";
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientsList => {
            for (let client of clientsList) {
                if (client.url === targetUrl && 'focus' in client) return client.focus();
            }
            return clients.openWindow(targetUrl);
        })
    );
});