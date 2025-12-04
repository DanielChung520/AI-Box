/** WARNING: DON'T EDIT THIS FILE */
/** WARNING: DON'T EDIT THIS FILE */
/** WARNING: DON'T EDIT THIS FILE */

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
import { VitePWA } from "vite-plugin-pwa";

function getPlugins() {
  const plugins = [
    react(),
    tsconfigPaths(),
    VitePWA({
      registerType: "prompt", // 改为 prompt，让用户手动更新，避免自动缓存
      // 排除大文件，使用 runtime caching 处理
      includeAssets: [],
      workbox: {
        // 排除大文件，只缓存小文件
        globPatterns: ["**/*.{js,css,html,ico,png,woff,woff2}"],
        // 排除 SVG 文件（太大，使用 runtime caching）
        globIgnores: ["**/*.svg"],
        // 增加文件大小限制（用于 JS 文件）
        maximumFileSizeToCacheInBytes: 20 * 1024 * 1024, // 20 MB
        runtimeCaching: [
          {
            // SVG 文件使用 runtime caching
            urlPattern: /\.svg$/i,
            handler: "CacheFirst",
            options: {
              cacheName: "svg-cache",
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
          {
            urlPattern: /^https:\/\/cdnjs\.cloudflare\.com\/.*/i,
            handler: "CacheFirst",
            options: {
              cacheName: "cdnjs-cache",
              expiration: {
                maxEntries: 10,
                maxAgeSeconds: 60 * 60 * 24 * 365, // 1 year
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
          {
            urlPattern: /^https:\/\/.*\.(?:png|jpg|jpeg|gif|webp)/i,
            handler: "CacheFirst",
            options: {
              cacheName: "images-cache",
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
              },
            },
          },
          {
            urlPattern: /\/api\/.*/i,
            handler: "NetworkFirst",
            options: {
              cacheName: "api-cache",
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 60 * 5, // 5 minutes
              },
              networkTimeoutSeconds: 10,
            },
          },
        ],
      },
      manifest: {
        name: "AI GenAI Chat Room",
        short_name: "AI Chat",
        description: "AI 生成式聊天室 - 智能對話助手平台",
        theme_color: "#9333ea",
        background_color: "#1a1a1a",
        display: "standalone",
        orientation: "portrait-primary",
        scope: "/",
        start_url: "/",
        icons: [
          {
            src: "/SmartQ.-logo.svg",
            sizes: "any",
            type: "image/svg+xml",
            purpose: "any maskable",
          },
        ],
        shortcuts: [
          {
            name: "開始聊天",
            short_name: "聊天",
            description: "開始新的對話",
            url: "/",
            icons: [
              {
                src: "/SmartQ.-logo.svg",
                sizes: "any",
                type: "image/svg+xml",
              },
            ],
          },
        ],
        categories: ["productivity", "utilities"],
      },
      devOptions: {
        enabled: false, // 暂时禁用开发时的 PWA，确保修改能及时生效
        type: "module",
      },
    }),
  ];
  return plugins;
}

export default defineConfig(({ mode }) => {
  // 加載環境變量
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: getPlugins(),
    server: {
      host: true,
      port: 3000,
      // 允許 Cloudflare Tunnel 域名
      allowedHosts: [
        'bot.k84.org',
        'localhost',
        '.localhost',
      ],
      // 配置 HMR WebSocket（用於代理環境）
      // 當通過 Cloudflare Tunnel 等代理訪問時，需要正確配置客戶端連接參數
      hmr: env.VITE_HMR_DISABLE === 'true'
        ? false // 完全禁用 HMR（如果 WebSocket 無法工作）
        : env.VITE_HMR_CLIENT_HOST || env.VITE_HMR_CLIENT_PORT
        ? {
            // 服務器在本地監聽（不設置 host，使用默認的 localhost）
            // 服務器監聽的本地端口（與 server.port 一致）
            port: 3000,
            // WebSocket 協議（wss 用於 HTTPS，ws 用於 HTTP）
            protocol: (env.VITE_HMR_PROTOCOL as 'ws' | 'wss') || 'wss',
            // 客戶端應該連接的主機名（代理域名，如 bot.k84.org）
            // 這告訴瀏覽器連接到代理域名而不是 localhost
            clientHost: env.VITE_HMR_CLIENT_HOST || undefined,
            // 客戶端應該連接的端口（代理端口，443 用於 HTTPS，80 用於 HTTP）
            // 這告訴瀏覽器連接到代理端口而不是本地端口
            clientPort: env.VITE_HMR_CLIENT_PORT ? parseInt(env.VITE_HMR_CLIENT_PORT) : 443,
          }
        : undefined, // 使用默認配置，Vite 會自動處理
      proxy: {
        // 代理 API 請求到後端服務器
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        // 代理版本端點
        '/version': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
