import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";
import { Toaster } from 'sonner';
import App from "./App.tsx";
import "./index.css";
import { performanceMonitor } from "./lib/performance.ts";

// 記錄 React 應用啟動時間
performanceMonitor.markReactAppStart();

// 初始化主题（在React应用启动前设置，避免闪烁）
(function initTheme() {
  const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null;
  const theme = savedTheme || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

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
