// 代碼功能說明: 系統服務狀態頁面
// 創建日期: 2026-01-17 22:45 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 18:29 UTC+8

import React, { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getServices, checkServiceHealth, ServiceStatus } from '@/lib/api';
import ServiceStatusCard from '@/components/SystemAdmin/ServiceStatusCard';
import ServiceLogViewer from '@/components/SystemAdmin/ServiceLogViewer';
import DashboardModal from '@/components/SystemAdmin/DashboardModal';

// 功能開關：是否使用新的 Prometheus 監控系統
const USE_NEW_MONITORING = import.meta.env.VITE_USE_NEW_MONITORING === 'true';

const SystemServiceStatus: React.FC = () => {
  const navigate = useNavigate();

  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedServiceForLogs, setSelectedServiceForLogs] = useState<string | null>(null);
  const [selectedServiceForDashboard, setSelectedServiceForDashboard] = useState<string | null>(null);
  const [selectedServiceForDetail, setSelectedServiceForDetail] = useState<ServiceStatus | null>(null);

  // 載入服務狀態
  const loadServices = async () => {
    try {
      // 根據功能開關選擇使用舊系統還是新系統
      // 後端已經根據 USE_NEW_MONITORING 環境變量自動切換
      // 前端只需要調用統一的 API 端點即可
      const result = await getServices();
      setServices(result);
    } catch (error) {
      console.error('Failed to load services:', error);
      // 顯示錯誤提示
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // 初始載入
  useEffect(() => {
    loadServices();
  }, []);

  // 自動刷新 (每 30 秒)
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadServices();
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  // 手動刷新
  const handleRefresh = () => {
    setRefreshing(true);
    loadServices();
  };

  // 返回上一頁或主頁
  const handleBack = () => {
    navigate('/home');
  };

  // 查看服務詳情
  const handleViewDetail = (serviceName: string) => {
    const service = services.find(s => s.service_name === serviceName);
    if (service) {
      setSelectedServiceForDetail(service);
    }
  };

  // 查看服務日誌
  const handleViewLogs = (serviceName: string) => {
    setSelectedServiceForLogs(serviceName);
  };

  // 打開 Dashboard
  const handleOpenDashboard = (serviceName: string) => {
    setSelectedServiceForDashboard(serviceName);
  };

  // 手動觸發健康檢查
  const handleCheckHealth = async (serviceName: string) => {
    try {
      await checkServiceHealth(serviceName);
      await loadServices(); // 重新載入服務狀態
    } catch (error) {
      console.error('Failed to check service health:', error);
    }
  };

  // 計算整體健康狀態
  const calculateOverallHealth = () => {
    if (services.length === 0) return { status: 'unknown', percentage: 0 };

    const healthyCount = services.filter(s => s.status === 'running' && s.health_status === 'healthy').length;
    const percentage = Math.round((healthyCount / services.length) * 100);

    if (percentage === 100) return { status: 'healthy', percentage };
    if (percentage >= 80) return { status: 'degraded', percentage };
    if (percentage >= 50) return { status: 'unhealthy', percentage };
    return { status: 'critical', percentage };
  };

  const overallHealth = calculateOverallHealth();

  // 獲取整體健康狀態的顏色
  const getOverallHealthColor = () => {
    switch (overallHealth.status) {
      case 'healthy':
        return 'text-green-600';
      case 'degraded':
        return 'text-yellow-600';
      case 'unhealthy':
        return 'text-orange-600';
      case 'critical':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

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
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">系統服務狀態</h1>
          </div>

          <div className="flex items-center space-x-4">
            {/* 自動刷新開關 */}
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">自動刷新</span>
            </label>

            {/* 刷新按鈕 */}
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
              <span>刷新</span>
            </button>

            {/* 設置按鈕 */}
            <button
              className="p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="設置"
            >
              <Settings size={20} />
            </button>
          </div>
        </div>

        {/* 整體健康狀態 */}
        <div className="mt-4 flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">整體健康狀態:</span>
            <span className={`text-lg font-semibold ${getOverallHealthColor()}`}>
              {overallHealth.percentage}%
            </span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              ({services.filter(s => s.status === 'running' && s.health_status === 'healthy').length} / {services.length})
            </span>
          </div>
        </div>
      </div>

      {/* 服務狀態卡片網格 */}
      <div className="px-6 py-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="animate-spin text-gray-400" size={32} />
            <span className="ml-3 text-gray-600 dark:text-gray-400">載入中...</span>
          </div>
        ) : services.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-600 dark:text-gray-400">沒有找到服務</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((service) => (
              <ServiceStatusCard
                key={service.service_name}
                service={service}
                onViewDetail={handleViewDetail}
                onViewLogs={handleViewLogs}
                onOpenDashboard={handleOpenDashboard}
              />
            ))}
          </div>
        )}
      </div>

      {/* 服務日誌查看器 Modal */}
      {selectedServiceForLogs && (
        <ServiceLogViewer
          serviceName={selectedServiceForLogs}
          onClose={() => setSelectedServiceForLogs(null)}
        />
      )}

      {/* Dashboard Modal */}
      {selectedServiceForDashboard && (
        <DashboardModal
          serviceName={selectedServiceForDashboard}
          onClose={() => setSelectedServiceForDashboard(null)}
        />
      )}

      {/* 服務詳情 Modal */}
      {selectedServiceForDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
          <div className="bg-white rounded-lg shadow-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                服務詳情: {selectedServiceForDetail.service_name}
              </h2>
              <button
                onClick={() => setSelectedServiceForDetail(null)}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
              >
                <ArrowLeft size={20} />
              </button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">服務名稱</h3>
                  <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.service_name}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">服務類型</h3>
                  <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.service_type}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">狀態</h3>
                  <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.status}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">健康狀態</h3>
                  <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.health_status}</p>
                </div>
                {selectedServiceForDetail.host && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">主機</h3>
                    <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.host}</p>
                  </div>
                )}
                {selectedServiceForDetail.port && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">端口</h3>
                    <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.port}</p>
                  </div>
                )}
                {selectedServiceForDetail.pid && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">進程 ID</h3>
                    <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.pid}</p>
                  </div>
                )}
                <div>
                  <h3 className="text-sm font-medium text-gray-500">檢查間隔</h3>
                  <p className="mt-1 text-base text-gray-900">{selectedServiceForDetail.check_interval}秒</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">最後檢查時間</h3>
                  <p className="mt-1 text-base text-gray-900">
                    {new Date(selectedServiceForDetail.last_check_at).toLocaleString('zh-TW')}
                  </p>
                </div>
                {selectedServiceForDetail.last_success_at && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-500">最後成功時間</h3>
                    <p className="mt-1 text-base text-gray-900">
                      {new Date(selectedServiceForDetail.last_success_at).toLocaleString('zh-TW')}
                    </p>
                  </div>
                )}
              </div>

              {selectedServiceForDetail.metadata && Object.keys(selectedServiceForDetail.metadata).length > 0 && (
                <div>
                  <h3 className="text-sm font-medium text-gray-500 mb-2">元數據</h3>
                  <div className="bg-gray-50 rounded-md p-4">
                    <pre className="text-xs text-gray-900 overflow-x-auto">
                      {JSON.stringify(selectedServiceForDetail.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              <div className="flex space-x-3 pt-4">
                <button
                  onClick={() => handleCheckHealth(selectedServiceForDetail.service_name)}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                >
                  觸發健康檢查
                </button>
                <button
                  onClick={() => {
                    handleViewLogs(selectedServiceForDetail.service_name);
                    setSelectedServiceForDetail(null);
                  }}
                  className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors"
                >
                  查看日誌
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemServiceStatus;
