import React, { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, Settings, MonitorPlay, Activity, ExternalLink, X, Maximize2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { getServices, checkServiceHealth, ServiceStatus } from '@/lib/api';
import ServiceStatusCard from '@/components/SystemAdmin/ServiceStatusCard';
import ServiceLogViewer from '@/components/SystemAdmin/ServiceLogViewer';
import DashboardModal from '@/components/SystemAdmin/DashboardModal';

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

  const [showGrafanaPopup, setShowGrafanaPopup] = useState(false);
  const [showPrometheusPopup, setShowPrometheusPopup] = useState(false);
  const [toolsExpanded, setToolsExpanded] = useState(false);

  const loadServices = async () => {
    try {
      const result = await getServices();
      setServices(result);
    } catch (error) {
      console.error('Failed to load services:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadServices();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      loadServices();
    }, 30000);

    return () => clearInterval(interval);
  }, [autoRefresh]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadServices();
  };

  const toggleToolsExpanded = () => {
    setToolsExpanded(!toolsExpanded);
  };

  const openGrafana = () => {
    setShowGrafanaPopup(true);
  };

  const openPrometheus = () => {
    setShowPrometheusPopup(true);
  };

  const closePopups = () => {
    setShowGrafanaPopup(false);
    setShowPrometheusPopup(false);
  };

  const openGrafanaDirect = () => {
    window.open('/api/v1/monitoring/grafana/', '_blank');
  };

  const openPrometheusDirect = () => {
    window.open('/api/v1/monitoring/prometheus/', '_blank');
  };

  const handleBack = () => {
    navigate('/home');
  };

  const handleViewDetail = (serviceName: string) => {
    const service = services.find(s => s.service_name === serviceName);
    if (service) {
      setSelectedServiceForDetail(service);
    }
  };

  const handleViewLogs = (serviceName: string) => {
    setSelectedServiceForLogs(serviceName);
  };

  const handleOpenDashboard = (serviceName: string) => {
    setSelectedServiceForDashboard(serviceName);
  };

  const handleCheckHealth = async (serviceName: string) => {
    try {
      await checkServiceHealth(serviceName);
      await loadServices();
    } catch (error) {
      console.error('Failed to check service health:', error);
    }
  };

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
      {/* 浮動監控工具按� */}
      <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50">
        <button
          onClick={toggleToolsExpanded}
          className="flex items-center space-x-2 bg-white dark:bg-gray-800 shadow-lg hover:shadow-xl rounded-full p-3 transition-all duration-300 border border-gray-200 dark:border-gray-700"
        >
          <MonitorPlay size={20} className="text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">監控工具</span>
        </button>

        {/* 浮動工具面板 */}
        {toolsExpanded && (
          <div className="absolute top-full left-0 mt-12 flex flex-col gap-2 bg-white dark:bg-gray-800 shadow-xl rounded-lg p-4 border border-gray-200 dark:border-gray-700 min-w-[200px]">

            {/* Grafana 選項 */}
            <button
              onClick={openGrafana}
              className="flex items-center space-x-3 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors w-full text-left"
            >
              <Activity size={18} className="text-orange-500" />
              <div className="flex-1">
                <div className="font-semibold text-gray-900 dark:text-white">Grafana</div>
                <div className="text-xs text-gray-600 dark:text-gray-400">儀表板與可視化</div>
              </div>
              <ExternalLink size={16} className="text-gray-400" />
            </button>

            {/* Prometheus 選項 */}
            <button
              onClick={openPrometheus}
              className="flex items-center space-x-3 p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors w-full text-left"
            >
              <Activity size={18} className="text-blue-600" />
              <div className="flex-1">
                <div className="font-semibold text-gray-900 dark:text-white">Prometheus</div>
                <div className="text-xs text-gray-600 dark:text-gray-400">指標查詢與數據存儲</div>
              </div>
              <ExternalLink size={16} className="text-gray-400" />
            </button>

            {/* 分隔線 */}
            <div className="border-t border-gray-200 dark:border-gray-700 my-2"></div>

            {/* 使用信息 */}
            <div className="text-xs text-gray-500 dark:text-gray-500">
              <div>點擊在浮動視窗中打開</div>
              <div>或直接訪問：3001 / 9090</div>
            </div>
          </div>
        )}
      </div>

      {/* Grafana 彈出視窗 */}
      {showGrafanaPopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-[800px] max-h-[90vh] overflow-auto">
            {/* 視窗標題欄 */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="p-2 bg-orange-500 rounded-lg">
                <Activity size={20} className="text-white" />
              </div>
              <div className="flex-1">
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">Grafana</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400">監控儀表板與數據可視化</p>
                </div>
              </div>
              <button
                onClick={() => setShowGrafanaPopup(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X size={20} className="text-gray-600 dark:text-gray-400" />
              </button>
            </div>

            {/* 視窗內容：iframe */}
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  在下方視窗中訪問 Grafana，或
                </p>
                <button
                  onClick={() => {
                    window.open('/api/v1/monitoring/grafana/', '_blank');
                    setShowGrafanaPopup(false);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <ExternalLink size={16} />
                  <span className="font-semibold">在新標籤頁打開</span>
                </button>
              </div>

              {/* 調整大小的按鈕 */}
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    const iframe = document.getElementById('grafana-iframe') as HTMLIFrameElement;
                    if (iframe) {
                      if (document.fullscreenElement) {
                        document.exitFullscreen();
                      } else {
                        iframe.requestFullscreen();
                      }
                    }
                  }}
                  id="grafana-maximize-btn"
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="全屏/還原"
                >
                  <Maximize2 size={18} className="text-gray-600 dark:text-gray-400" />
                </button>
              </div>
            </div>

            {/* 直接在當前頁面顯示 Grafana 連接信息 */}
            <div className="w-full h-[600px] border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center bg-gray-50 dark:bg-gray-800">
              <div className="text-center">
                <MonitorPlay className="mx-auto mb-4 text-blue-600" size={64} />
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Grafana 監控儀表板</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  點擊下方按鈕在新的分頁中開啟 Grafana
                </p>
                <button
                  onClick={() => {
                    window.open('https://gfn.k84.org', '_blank');
                    setShowGrafanaPopup(false);
                  }}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
                >
                  開啟 Grafana
                </button>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-3">
                  使用預設帳號：admin / admin
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Prometheus 彈出視窗 */}
      {showPrometheusPopup && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-[800px] max-h-[90vh] overflow-auto">
            {/* 視窗標題欄 */}
            <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Activity size={20} className="text-white" />
              </div>
              <div className="flex-1">
                <div>
                  <h2 className="text-xl font-bold text-gray-900 dark:text-white">Prometheus</h2>
                  <p className="text-sm text-gray-600 dark:text-gray-400">指標查詢與數據存儲</p>
                </div>
              </div>
              <button
                onClick={() => setShowPrometheusPopup(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X size={20} className="text-gray-600 dark:text-gray-400" />
              </button>
            </div>

            {/* 視窗內容：iframe */}
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  在下方視窗中訪問 Prometheus，或
                </p>
                <button
                  onClick={() => {
                    window.open('https://pmt.k84.org', '_blank');
                    setShowPrometheusPopup(false);
                  }}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <ExternalLink size={16} />
                  <span className="font-semibold">在新標籤頁打開</span>
                </button>
              </div>

              {/* 調整大小的按鈕 */}
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    const iframe = document.getElementById('prometheus-iframe') as HTMLIFrameElement;
                    if (iframe) {
                      if (document.fullscreenElement) {
                        document.exitFullscreen();
                      } else {
                        iframe.requestFullscreen();
                      }
                    }
                  }}
                  id="prometheus-maximize-btn"
                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  title="全屏/還原"
                >
                  <Maximize2 size={18} className="text-gray-600 dark:text-gray-400" />
                </button>
              </div>
            </div>

            {/* 直接在當前頁面顯示 Prometheus 連接信息 */}
            <div className="w-full h-[600px] border border-gray-200 dark:border-gray-700 rounded-lg flex items-center justify-center bg-gray-50 dark:bg-gray-800">
              <div className="text-center">
                <Activity className="mx-auto mb-4 text-blue-600" size={64} />
                <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-2">Prometheus 指標查詢</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  點擊下方按鈕在新的分頁中開啟 Prometheus
                </p>
                <button
                  onClick={() => {
                    window.open('https://pmt.k84.org', '_blank');
                    setShowPrometheusPopup(false);
                  }}
                  className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
                >
                  開啟 Prometheus
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

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
                  {selectedServiceForDetail.last_check_at ? new Date(selectedServiceForDetail.last_check_at).toLocaleString('zh-TW') : '-'}
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
