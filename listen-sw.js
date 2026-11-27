// N4 聽力頁：離線用。只處理頁面導覽（先連網，失敗或太慢就用快取）；音檔由頁面自己從快取讀。
const PAGE_CACHE = 'n4listen-pages';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.mode !== 'navigate') return;
  e.respondWith((async () => {
    const cache = await caches.open(PAGE_CACHE);
    try {
      const net = await Promise.race([
        fetch(req),
        new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 5000))
      ]);
      if (net && net.ok) cache.put(req, net.clone());
      return net;
    } catch (err) {
      const hit = await cache.match(req, { ignoreSearch: true });
      if (hit) return hit;
      throw err;
    }
  })());
});
