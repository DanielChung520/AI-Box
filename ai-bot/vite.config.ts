/** WARNING: DON'T EDIT THIS FILE */
/** WARNING: DON'T EDIT THIS FILE */
/** WARNING: DON'T EDIT THIS FILE */

import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tsconfigPaths from "vite-tsconfig-paths";
// import { VitePWA } from "vite-plugin-pwa";

function getPlugins() {
  const plugins = [
    react(),
    tsconfigPaths(),
    // VitePWA temporarily disabled to fix API request issue
  ];
  return plugins;
}

export default defineConfig(({ mode }) => {
  // 加載環境變量
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: getPlugins(),
    // 配置中间件，允许所有主机访问（用于 Cloudflare Tunnel 等代理场景）
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        // 允许所有 Host header，解决 "Blocked request. This host is not allowed" 错误
        // 这是 Vite 6 的安全检查机制
        const host = req.headers.host;
        if (host && (host.includes('iee.k84.org') || host.includes('localhost') || host.includes('127.0.0.1'))) {
          next();
        } else {
          next();
        }
      });
    },
    server: {
      host: true, // 允许外部访问，等同于 '0.0.0.0'
      port: 3000,
      strictPort: false,
      // 允许的主机名列表（用于防止 DNS 重绑定攻击）
      // 当通过代理访问（如 Cloudflare Tunnel）时，需要明确允许代理域名
      allowedHosts: [
        'iee.k84.org',
        '192.168.10.131', 
        'iee.sunlyc.com',     // 代理域名
        'localhost',        // 本地开发
        '127.0.0.1',        // 本地 IP
        '.localhost',       // localhost 子域名
      ],
      // 配置 HMR WebSocket（用於代理環境）
      // 修改時間：2026-01-17 - 優化 HMR 配置，在代理環境中禁用 HMR 以避免 WebSocket 連接錯誤
      // 當通過 Cloudflare Tunnel 等代理訪問時，WebSocket 連接通常無法正常工作
      hmr: (() => {
        // 如果明確禁用 HMR，直接返回 false
        if (env.VITE_HMR_DISABLE === 'true') {
          return false;
        }

        // 檢測是否為代理環境：如果配置了 VITE_HMR_CLIENT_HOST，則為代理環境
        const isProxyAccess = !!env.VITE_HMR_CLIENT_HOST;

        // 在代理環境中禁用 HMR，避免 WebSocket 連接錯誤
        // 用戶可以手動刷新頁面來查看更新
        if (isProxyAccess) {
          console.info('[Vite] HMR disabled in proxy environment to avoid WebSocket connection errors');
          return false;
        }

        // 本地開發環境配置（直接訪問 localhost）
        return {
          port: 3000,
          protocol: 'ws',
          // 本地開發不需要指定 clientHost 和 clientPort，使用默認值
        };
      })(),
      proxy: {
        // 代理 API 請求到後端服務器
        '/api': {
          target: env.VITE_API_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
          // 確保 Cookie 正確傳遞到 Grafana 代理
          cookieDomainRewrite: {
            '*': '',
          },
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
