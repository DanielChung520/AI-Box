// 代碼功能說明: 系統監控頁面（嵌入 Grafana 儀表板）
// 創建日期: 2026-01-18 17:28 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 17:28 UTC+8

import React, { useState, useEffect, useContext } from 'react';
import { ArrowLeft, RefreshCw, ExternalLink, BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '@/contexts/authContext';
import { isSystemAdmin } from '@/lib/userUtils';
import { useLanguage } from '@/contexts/languageContext';
import { useTheme } from '@/hooks/useTheme';

// Grafana 儀表板配置
interface Dashboard {
  id: string;
  name: string;
  uid: string;
  description?: string;
}

const SystemMonitoring: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useContext(AuthContext);
  const { t } = useLanguage();
  const { theme } = useTheme();

  // 權限檢查
  const isAdmin = isSystemAdmin(currentUser);

  // 從環境變量獲取 Grafana URL（默認 localhost:3001）
  const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL || 'http://localhost:3001';

  // 儀表板列表
  const [dashboards] = useState<Dashboard[]>([
    {
      id: 'system-overview',
      name: '系統概覽',
      uid: 'system-overview',
      description: '整體系統健康狀況和資源使用情況',
    },
    {
      id: 'service-status',
      name: '服務狀態',
      uid: 'service-status',
      description: '各服務可用性和響應時間',
    },
    {
      id: 'performance',
      name: '性能監控',
      uid: 'performance',
      description: 'API 性能和請求統計',
    },
    {
      id: 'node-exporter',
      name: '系統資源',
      uid: '1860', // Node Exporter Full dashboard ID
      description: '系統級資源監控（CPU、內存、磁盤、網絡）',
    },
    {
      id: 'redis',
      name: 'Redis 監控',
      uid: '11835', // Redis Dashboard ID
      description: 'Redis 性能和連接狀態',
    },
  ]);

  // 當前選中的儀表板
  const [selectedDashboard, setSelectedDashboard] = useState<Dashboard>(dashboards[0]);

  // iframe 刷新計數器（用於強制刷新）
  const [iframeKey, setIframeKey] = useState(0);

  // 如果不是系統管理員，重定向到主頁
  useEffect(() => {
    if (!isAdmin) {
      navigate('/home', { replace: true });
    }
  }, [isAdmin, navigate]);

  // 返回上一頁
  const handleBack = () => {
    navigate('/home');
  };

  // 刷新儀表板
  const handleRefresh = () => {
    setIframeKey((prev) => prev + 1);
  };

  // 在新窗口打開 Grafana
  const handleOpenInNewTab = () => {
    const dashboardUrl = `${GRAFANA_URL}/d/${selectedDashboard.uid}/${selectedDashboard.id}`;
    window.open(dashboardUrl, '_blank', 'noopener,noreferrer');
  };

  // 獲取 iframe URL（包含主題參數）
  const getIframeUrl = (dashboard: Dashboard): string => {
    // Grafana 主題參數（light 或 dark）
    const grafanaTheme = theme === 'dark' ? 'dark' : 'light';

    // 構建 URL，包含主題和其他參數
    const params = new URLSearchParams({
      theme: grafanaTheme,
      kiosk: 'tv', // 隱藏 Grafana 導航欄
      refresh: '15s', // 自動刷新間隔
    });

    return `${GRAFANA_URL}/d/${dashboard.uid}/${dashboard.id}?${params.toString()}`;
  };

  if (!isAdmin) {
    return null; // 權限檢查失敗，不顯示內容
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 頂部導航欄 */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              <ArrowLeft size={20} />
              <span>返回</span>
            </button>
            <div className="h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
            <BarChart3 size={24} className="text-blue-600 dark:text-blue-400" />
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">系統監控</h1>
          </div>

          <div className="flex items-center space-x-3">
            {/* 刷新按鈕 */}
            <button
              onClick={handleRefresh}
              className="flex items-center space-x-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="刷新儀表板"
            >
              <RefreshCw size={16} />
              <span>刷新</span>
            </button>

            {/* 在新窗口打開 */}
            <button
              onClick={handleOpenInNewTab}
              className="flex items-center space-x-2 px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              title="在新窗口打開"
            >
              <ExternalLink size={16} />
              <span>新窗口</span>
            </button>
          </div>
        </div>

        {/* 儀表板選擇器 */}
        <div className="mt-4 flex items-center space-x-2 overflow-x-auto">
          {dashboards.map((dashboard) => (
            <button
              key={dashboard.id}
              onClick={() => setSelectedDashboard(dashboard)}
              className={`px-4 py-2 rounded-md whitespace-nowrap transition-colors ${
                selectedDashboard.id === dashboard.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {dashboard.name}
            </button>
          ))}
        </div>

        {/* 儀表板描述 */}
        {selectedDashboard.description && (
          <div className="mt-3 text-sm text-gray-600 dark:text-gray-400">
            {selectedDashboard.description}
          </div>
        )}
      </div>

      {/* Grafana iframe */}
      <div className="h-[calc(100vh-200px)] p-6">
        <div className="h-full bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden">
          <iframe
            key={iframeKey}
            src={getIframeUrl(selectedDashboard)}
            className="w-full h-full border-0"
            title={`Grafana - ${selectedDashboard.name}`}
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms"
            loading="lazy"
          />
        </div>
      </div>

      {/* 連接提示（如果 Grafana 不可用） */}
      <div className="px-6 pb-6">
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <div className="flex items-start space-x-3">
            <BarChart3 size={20} className="text-blue-600 dark:text-blue-400 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-900 dark:text-blue-200">
                提示
              </h3>
              <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                如果儀表板無法加載，請確認 Grafana 服務已啟動（
                <code className="px-1 py-0.5 bg-blue-100 dark:bg-blue-900/40 rounded text-xs">
                  {GRAFANA_URL}
                </code>
                ）。您可以運行{' '}
                <code className="px-1 py-0.5 bg-blue-100 dark:bg-blue-900/40 rounded text-xs">
                  docker-compose -f docker-compose.monitoring.yml up -d
                </code>{' '}
                啟動監控服務。
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemMonitoring;
