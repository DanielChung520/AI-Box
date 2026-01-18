// 代碼功能說明: Service Worker for PWA offline support
// 創建日期: 2026-01-17 18:48 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 11:05 UTC+8

// 臨時禁用緩存用於調試（修改時間：2026-01-18 11:05）
const DISABLE_CACHE = true;  // 設置為 true 以禁用所有緩存，便於調試

const CACHE_NAME = 'aibox-admin-v3';  // 更新版本號以清除舊緩存
const OFFLINE_URL = '/offline.html';

// 需要緩存的靜態資源
const STATIC_CACHE_URLS = [
  '/',
  '/offline.html',
  '/manifest.json',
  '/icon-192x192.png',
  '/icon-512x512.png',
];

// 需要緩存的 API 路徑（用於離線狀態）
const API_CACHE_URLS = [
  '/api/admin/services',
];

// Service Worker 安裝事件
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Installing...');

  if (DISABLE_CACHE) {
    console.log('[Service Worker] Cache DISABLED for debugging');
    self.skipWaiting();
    return;
  }

  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      console.log('[Service Worker] Caching static resources');

      try {
        await cache.addAll(STATIC_CACHE_URLS);
      } catch (error) {
        console.error('[Service Worker] Failed to cache static resources:', error);
      }
    })()
  );

  // 強制新的 Service Worker 立即激活
  self.skipWaiting();
});

// Service Worker 激活事件
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activating...');

  event.waitUntil(
    (async () => {
      // 清理所有舊的緩存
      const cacheNames = await caches.keys();
      await Promise.all(
        cacheNames.map((name) => {
          console.log('[Service Worker] Deleting cache:', name);
          return caches.delete(name);
        })
      );

      // 立即控制所有客戶端
      await self.clients.claim();
      console.log('[Service Worker] All caches cleared');
    })()
  );
});

// Service Worker fetch 事件
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 如果禁用緩存，直接從網絡獲取
  if (DISABLE_CACHE) {
    event.respondWith(
      fetch(request).catch(() => {
        // 如果是導航請求且網絡失敗，返回離線頁面
        if (request.mode === 'navigate') {
          return caches.match(OFFLINE_URL) || new Response('Offline', {
            status: 503,
            statusText: 'Service Unavailable',
          });
        }
        throw new Error('Network request failed');
      })
    );
    return;
  }

  // 只處理 GET 請求
  if (request.method !== 'GET') {
    return;
  }

  // API 請求使用 Network First 策略（帶緩存備份）
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      (async () => {
        try {
          // 嘗試從網絡獲取
          const networkResponse = await fetch(request);

          // 如果成功，緩存響應（僅緩存服務狀態 API）
          if (
            networkResponse.ok &&
            API_CACHE_URLS.some((path) => url.pathname.startsWith(path))
          ) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
          }

          return networkResponse;
        } catch (error) {
          console.log('[Service Worker] Network request failed, trying cache:', url.pathname);

          // 網絡失敗，嘗試從緩存讀取
          const cachedResponse = await caches.match(request);

          if (cachedResponse) {
            console.log('[Service Worker] Serving from cache:', url.pathname);
            return cachedResponse;
          }

          // 如果緩存也沒有，返回離線頁面
          console.log('[Service Worker] No cache available, returning offline page');
          return caches.match(OFFLINE_URL);
        }
      })()
    );
    return;
  }

  // 靜態資源使用 Cache First 策略
  event.respondWith(
    (async () => {
      // 先嘗試從緩存讀取
      const cachedResponse = await caches.match(request);

      if (cachedResponse) {
        console.log('[Service Worker] Serving from cache:', url.pathname);
        return cachedResponse;
      }

      // 緩存沒有，從網絡獲取
      try {
        const networkResponse = await fetch(request);

        // 緩存新的靜態資源
        if (networkResponse.ok) {
          const cache = await caches.open(CACHE_NAME);
          cache.put(request, networkResponse.clone());
        }

        return networkResponse;
      } catch (error) {
        console.log('[Service Worker] Network request failed:', url.pathname);

        // 如果是導航請求，返回離線頁面
        if (request.mode === 'navigate') {
          return caches.match(OFFLINE_URL);
        }

        // 其他請求返回空響應
        return new Response('Offline', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: new Headers({
            'Content-Type': 'text/plain',
          }),
        });
      }
    })()
  );
});

// Service Worker 消息事件（用於手動觸發緩存更新）
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SYNC_SERVICE_STATUS') {
    if (DISABLE_CACHE) {
      console.log('[Service Worker] Cache disabled, skipping sync');
      return;
    }

    console.log('[Service Worker] Syncing service status...');

    event.waitUntil(
      (async () => {
        try {
          const response = await fetch('/api/admin/services');

          if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put('/api/admin/services', response.clone());
            console.log('[Service Worker] Service status synced successfully');
          }
        } catch (error) {
          console.error('[Service Worker] Failed to sync service status:', error);
        }
      })()
    );
  }

  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[Service Worker] Skipping waiting...');
    self.skipWaiting();
  }
});
