// AcousticAcre service worker: app shell + AI models + phrase packs work fully offline
// after the first online visit. Bump CACHE when models or content change.
const CACHE = 'acousticacre-v10-ai';
const PACK_CACHE = 'acousticacre-packs';   // packs installed from files: never deleted by updates
const PRECACHE = [
  '/', '/index.html', '/manifest.webmanifest',
  '/ort/ort.js', '/ai-worker.js',
  '/models/crop/manifest.json', '/models/crop/labels.json', '/models/crop/model.onnx',
  '/models/machine/manifest.json', '/models/machine/labels.json', '/models/machine/model.onnx',
  '/models/machine/dsp_constants.json',
  '/content/diagnoses.json', '/content/phrases/en.json', '/content/phrases/ha.json',
];
// ONNX Runtime's WebAssembly files have version-specific names: listed at build time if present
const OPTIONAL = ['/ort/ort-wasm-simd-threaded.wasm', '/ort/ort-wasm-simd-threaded.mjs',
                  '/ort/ort-wasm-simd.wasm', '/ort/ort-wasm.wasm'];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(PRECACHE);
    await Promise.all(OPTIONAL.map(u => cache.add(u).catch(() => undefined)));
    // voice clips: each language folder has a _manifest.json listing its clip ids (made by make_clips.py)
    for (const lang of ['ha', 'en']) {
      try {
        const m = await (await fetch(`/clips/${lang}/_manifest.json`)).json();
        const ids = Object.keys(m.clips || {});
        await Promise.all(ids.map(id => cache.add(`/clips/${lang}/${id}.mp3`).catch(() => undefined)));
      } catch { /* no clips for this language yet */ }
    }
  })());
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE && key !== PACK_CACHE).map(key => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put('/index.html', copy));
        }
        return response;
      }).catch(() => caches.match('/index.html'))
    );
    return;
  }

  // cache-first for everything else (JS/CSS bundles, models, clips, phrases)
  event.respondWith(
    caches.match(request).then(cached => {
      if (cached) return cached;
      return fetch(request).then(response => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(CACHE).then(cache => cache.put(request, copy));
        }
        return response;
      });
    })
  );
});
