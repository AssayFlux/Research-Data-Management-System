/*
 * Research Data Management System
 * Production PWA Service Worker
 *
 * IMPORTANT:
 * This application handles research data.
 * Authenticated/application responses are NOT cached.
 * Only safe static assets are cached.
 */

const CACHE_NAME = "research-dms-static-v1";

const STATIC_ASSETS = [
  "/static/manifest.json",
  "/static/css/pro.css",
  "/static/css/fonts.css",
  "/static/css/gradients.css",
  "/static/js/app.js",
  "/static/js/navigation.js",
  "/static/js/colorpicker.js",
  "/static/vendor/chart.umd.min.js",
  "/static/vendor/lucide.min.js"
];

/* Install */
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .catch(() => {})
  );

  self.skipWaiting();
});

/* Activate */
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );

  self.clients.claim();
});

/* Fetch */
self.addEventListener("fetch", event => {
  const request = event.request;

  if (request.method !== "GET") {
    return;
  }

  const url = new URL(request.url);

  /* Never handle external resources */
  if (url.origin !== self.location.origin) {
    return;
  }

  /*
   * Only cache files under /static/.
   * Flask routes such as /participants, /records,
   * /analysis, /export, /settings, etc. are deliberately
   * fetched from the server every time.
   */
  if (!url.pathname.startsWith("/static/")) {
    return;
  }

  event.respondWith(
    caches.match(request).then(cached => {
      const network = fetch(request)
        .then(response => {
          if (response && response.ok) {
            const copy = response.clone();

            caches.open(CACHE_NAME)
              .then(cache => cache.put(request, copy))
              .catch(() => {});
          }

          return response;
        })
        .catch(() => cached);

      return cached || network;
    })
  );
});
