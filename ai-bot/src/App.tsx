import { Routes, Route, Navigate, useSearchParams } from "react-router-dom";
import Home from "@/pages/Home";
import FileManagement from "@/pages/FileManagement";
import DocumentAssistant from "@/pages/DocumentAssistant";
import IEEEditor from "@/pages/IEEEditor";
import WelcomePage from "@/pages/WelcomePage";
import LoginPage from "@/pages/LoginPage";
import SystemServiceStatus from "@/pages/SystemServiceStatus";
import SystemMonitoring from "@/pages/SystemMonitoring";
import AccountSecuritySettings from "@/pages/AccountSecuritySettings";
import SystemSettings from "@/pages/SystemSettings";
import AgentRequestManagement from "@/pages/AgentRequestManagement";
import { useState, useEffect } from "react";
import { AuthContext, User } from '@/contexts/authContext';
import { LanguageProvider, useLanguage } from '@/contexts/languageContext';
import { FileEditingProvider } from '@/contexts/fileEditingContext';
import { performanceMonitor } from '@/lib/performance';
import { isSystemAdmin } from '@/lib/userUtils';

// IEE Editor Wrapper 組件，用於從 URL 參數獲取 fileId
function IEEEditorWrapper() {
  const [searchParams] = useSearchParams();
  const fileId = searchParams.get('fileId') || undefined;

  return <IEEEditor fileId={fileId} />;
}

// 權限檢查組件 - 系統管理員權限
interface AdminRouteProps {
  children: JSX.Element;
}

function AdminRoute({ children }: AdminRouteProps) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem('isAuthenticated') === 'true';
  });

  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    const userJson = localStorage.getItem('currentUser');
    return userJson ? JSON.parse(userJson) : null;
  });

  // 使用統一的系統管理員檢查函數
  const isAdmin = isSystemAdmin(currentUser);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (!isAdmin) {
    return <Navigate to="/home" replace />;
  }

  return children;
}

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    // 從 localStorage 讀取登錄狀態
    return localStorage.getItem('isAuthenticated') === 'true';
  });

  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    // 從 localStorage 讀取用戶信息
    const userJson = localStorage.getItem('currentUser');
    return userJson ? JSON.parse(userJson) : null;
  });

  const { t } = useLanguage();

  useEffect(() => {
    // 記錄 React 應用準備完成時間
    performanceMonitor.markReactAppReady();

    // 監聽 localStorage 變化（跨標籤頁）
    const handleStorageChange = () => {
      setIsAuthenticated(localStorage.getItem('isAuthenticated') === 'true');
      const userJson = localStorage.getItem('currentUser');
      setCurrentUser(userJson ? JSON.parse(userJson) : null);
    };

    // 監聽自定義事件（同標籤頁內的認證狀態變化）
    const handleAuthStateChanged = (event?: CustomEvent) => {
      setIsAuthenticated(localStorage.getItem('isAuthenticated') === 'true');
      // 優先使用事件中的 currentUser，否則從 localStorage 讀取
      if (event?.detail?.currentUser) {
        setCurrentUser(event.detail.currentUser);
        localStorage.setItem('currentUser', JSON.stringify(event.detail.currentUser));
      } else {
        const userJson = localStorage.getItem('currentUser');
        setCurrentUser(userJson ? JSON.parse(userJson) : null);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('authStateChanged', handleAuthStateChanged as EventListener);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('authStateChanged', handleAuthStateChanged as EventListener);
    };
  }, []);

  const logout = () => {
    // 清除所有認證相關的 localStorage
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('userEmail');
    localStorage.removeItem('userName');
    localStorage.removeItem('user_id');
    localStorage.removeItem('currentUser');

    // 更新狀態
    setIsAuthenticated(false);
    setCurrentUser(null);

    // 觸發自定義事件，通知其他組件認證狀態已改變
    window.dispatchEvent(new CustomEvent('authStateChanged'));
  };

  return (
    <AuthContext.Provider
      value={{ isAuthenticated, setIsAuthenticated, logout, currentUser, setCurrentUser }}
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

        {/* 系統管理路由 - 需要系統管理員權限 */}
        <Route
          path="/admin/services"
          element={
            <AdminRoute>
              <SystemServiceStatus />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/monitoring"
          element={
            <AdminRoute>
              <SystemMonitoring />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/accounts"
          element={
            <AdminRoute>
              <AccountSecuritySettings />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <AdminRoute>
              <SystemSettings />
            </AdminRoute>
          }
        />
        <Route
          path="/admin/agent-requests"
          element={
            <AdminRoute>
              <AgentRequestManagement />
            </AdminRoute>
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
