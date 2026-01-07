import { Routes, Route, Navigate, useSearchParams } from "react-router-dom";
import Home from "@/pages/Home";
import FileManagement from "@/pages/FileManagement";
import DocumentAssistant from "@/pages/DocumentAssistant";
import IEEEditor from "@/pages/IEEEditor";
import WelcomePage from "@/pages/WelcomePage";
import LoginPage from "@/pages/LoginPage";
import { useState, useEffect } from "react";
import { AuthContext } from '@/contexts/authContext';
import { LanguageProvider, useLanguage } from '@/contexts/languageContext';
import { FileEditingProvider } from '@/contexts/fileEditingContext';
import { performanceMonitor } from '@/lib/performance';

// IEE Editor Wrapper 組件，用於從 URL 參數獲取 fileId
function IEEEditorWrapper() {
  const [searchParams] = useSearchParams();
  const fileId = searchParams.get('fileId') || undefined;

  return <IEEEditor fileId={fileId} />;
}

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    // 從 localStorage 讀取登錄狀態
    return localStorage.getItem('isAuthenticated') === 'true';
  });
  const { t } = useLanguage();

  useEffect(() => {
    // 記錄 React 應用準備完成時間
    performanceMonitor.markReactAppReady();

    // 監聽 localStorage 變化（跨標籤頁）
    const handleStorageChange = () => {
      setIsAuthenticated(localStorage.getItem('isAuthenticated') === 'true');
    };

    // 監聽自定義事件（同標籤頁內的認證狀態變化）
    const handleAuthStateChanged = () => {
      setIsAuthenticated(localStorage.getItem('isAuthenticated') === 'true');
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('authStateChanged', handleAuthStateChanged);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('authStateChanged', handleAuthStateChanged);
    };
  }, []);

  const logout = () => {
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, setIsAuthenticated, logout }}
    >
      <FileEditingProvider>
        <Routes>
        {/* 歡迎頁面 - 首次進入 */}
        <Route path="/" element={<WelcomePage />} />

        {/* 登錄頁面 */}
        <Route path="/login" element={<LoginPage />} />

        {/* 主頁面 - 需要認證 */}
        <Route
          path="/home"
          element={
            isAuthenticated ? <Home /> : <Navigate to="/login" replace />
          }
        />

        {/* 文件管理 - 需要認證 */}
        <Route
          path="/files"
          element={
            isAuthenticated ? <FileManagement /> : <Navigate to="/login" replace />
          }
        />

        {/* 文件助手 - 需要認證 */}
        <Route
          path="/docs"
          element={
            isAuthenticated ? <DocumentAssistant /> : <Navigate to="/login" replace />
          }
        />

        {/* IEE 編輯器 - 需要認證 */}
        <Route
          path="/iee-editor"
          element={
            isAuthenticated ? <IEEEditorWrapper /> : <Navigate to="/login" replace />
          }
        />

        {/* 其他頁面 */}
        <Route
          path="/other"
          element={
            isAuthenticated ? (
              <div className="text-center text-xl">{t('common.otherPage')}</div>
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />

        {/* 默認重定向 */}
        <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </FileEditingProvider>
    </AuthContext.Provider>
  );
}

export default function App() {
  return (
    <LanguageProvider>
      <AppContent />
    </LanguageProvider>
  );
}
