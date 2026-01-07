import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { Toaster } from 'sonner';
import App from "./App.tsx";
import "./index.css";
import { performanceMonitor } from "./lib/performance.ts";

// 修改時間：2026-01-06 - 優雅處理 Vite HMR WebSocket 連接失敗
// 在代理環境下（如 Cloudflare Tunnel），WebSocket 可能無法連接，但不影響應用正常使用
(function suppressHMRWebSocketErrors() {
  // 只在開發環境處理（生產環境不會有 HMR）
  if (import.meta.env.DEV) {
    // 攔截 console.error，過濾 WebSocket 連接錯誤
    const originalError = console.error;
    console.error = (...args: any[]) => {
      // 過濾掉 Vite HMR WebSocket 相關的錯誤
      const message = args[0]?.toString() || '';
      const errorMessage = args[1]?.toString() || '';
      const combinedMessage = message + ' ' + errorMessage;

      if (
        (message.includes('WebSocket connection to') ||
         message.includes('WebSocket') ||
         errorMessage.includes('WebSocket')) &&
        (message.includes('failed') ||
         message.includes('wss://') ||
         message.includes('ws://') ||
         combinedMessage.includes('iee.k84.org'))
      ) {
        // 靜默處理，不輸出到控制台
        // 如果需要調試，可以取消下面的註釋
        // console.debug('[HMR] WebSocket connection failed (expected in proxy environments)', args);
        return;
      }
      // 其他錯誤正常輸出
      originalError.apply(console, args);
    };

    // 攔截 console.warn，過濾 WebSocket 相關警告
    const originalWarn = console.warn;
    console.warn = (...args: any[]) => {
      const message = args[0]?.toString() || '';
      if (
        message.includes('WebSocket') ||
        message.includes('wss://') ||
        message.includes('ws://') ||
        message.includes('iee.k84.org')
      ) {
        return; // 靜默處理
      }
      originalWarn.apply(console, args);
    };

    // 監聽全局錯誤事件，過濾 WebSocket 相關錯誤
    window.addEventListener('error', (event) => {
      const errorMessage = event.message || '';
      const errorSource = event.filename || '';
      if (
        errorMessage.includes('WebSocket') ||
        errorMessage.includes('wss://') ||
        errorMessage.includes('ws://') ||
        errorSource.includes('client') // Vite client 相關錯誤
      ) {
        event.preventDefault(); // 阻止錯誤冒泡
        return false;
      }
    }, true); // 使用捕獲階段，優先處理

    // 監聽未處理的 Promise 拒絕（可能包含 WebSocket 錯誤）
    window.addEventListener('unhandledrejection', (event) => {
      const reason = event.reason?.toString() || '';
      if (
        reason.includes('WebSocket') ||
        reason.includes('wss://') ||
        reason.includes('ws://')
      ) {
        event.preventDefault(); // 阻止錯誤冒泡
        return false;
      }
    });
  }
})();

// 記錄 React 應用啟動時間
performanceMonitor.markReactAppStart();

// 初始化主题（在React应用启动前设置，避免闪烁）
(function initTheme() {
  const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
  // 修改時間：2025-12-12 - 將登錄後的默認主題設置為深色
  const theme = savedTheme || 'dark';

  // 设置主题类
  document.documentElement.classList.remove('light', 'dark');
  document.documentElement.classList.add(theme);

  // Tailwind darkMode: "class" 需要 'dark' 类
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
})();

// 隱藏內聯歡迎頁的函數
function hideInitialWelcome() {
  const initialWelcome = document.getElementById('initial-welcome');
  if (initialWelcome) {
    initialWelcome.classList.add('hidden');
    // 動畫完成後移除元素
    setTimeout(() => {
      initialWelcome.remove();
    }, 500);
  }
}

const root = createRoot(document.getElementById("root")!);

root.render(
  <StrictMode>
    <HashRouter>
      <App />
      <Toaster />
    </HashRouter>
  </StrictMode>
);

// React 應用渲染完成後，隱藏內聯歡迎頁
// 使用 requestAnimationFrame 確保 DOM 更新完成
requestAnimationFrame(() => {
  setTimeout(() => {
    hideInitialWelcome();
  }, 100);
});
