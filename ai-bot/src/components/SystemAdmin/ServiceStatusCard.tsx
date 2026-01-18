// 代碼功能說明: 服務狀態卡片組件
// 創建日期: 2026-01-17 22:30 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-17 22:30 UTC+8

import React from 'react';
import { ServiceStatus } from '@/lib/api';
import { useLanguage } from '@/hooks/useLanguage';

interface ServiceStatusCardProps {
  service: ServiceStatus;
  onViewDetail: (serviceName: string) => void;
  onViewLogs: (serviceName: string) => void;
  onOpenDashboard?: (serviceName: string) => void;
}

const ServiceStatusCard: React.FC<ServiceStatusCardProps> = ({
  service,
  onViewDetail,
  onViewLogs,
  onOpenDashboard,
}) => {
  const { t } = useLanguage();

  // 根據服務狀態返回對應的圖標和顏色
  const getStatusIcon = () => {
    if (service.status === 'running' && service.health_status === 'healthy') {
      return { icon: '🟢', color: 'text-green-600', bg: 'bg-green-50' };
    }
    if (service.status === 'running' && service.health_status === 'degraded') {
      return { icon: '🟡', color: 'text-yellow-600', bg: 'bg-yellow-50' };
    }
    if (service.status === 'error' || service.health_status === 'unhealthy') {
      return { icon: '🔴', color: 'text-red-600', bg: 'bg-red-50' };
    }
    return { icon: '⚪', color: 'text-gray-600', bg: 'bg-gray-50' };
  };

  const statusInfo = getStatusIcon();

  // 格式化時間
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000); // 秒

    if (diff < 60) return `${diff} 秒前`;
    if (diff < 3600) return `${Math.floor(diff / 60)} 分鐘前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小時前`;
    return date.toLocaleString('zh-TW');
  };

  // 判斷服務是否有 Dashboard
  const hasDashboard = ['arangodb', 'rq', 'seaweedfs'].includes(service.service_name.toLowerCase());

  return (
    <div className={`rounded-lg border ${statusInfo.bg} border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow`}>
      {/* 服務名稱和狀態圖標 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">{statusInfo.icon}</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {service.service_name}
            </h3>
            <p className={`text-sm ${statusInfo.color} font-medium`}>
              {service.status === 'running' ? '運行中' : service.status === 'stopped' ? '已停止' : service.status === 'error' ? '異常' : '未知'}
            </p>
          </div>
        </div>
        {service.port && (
          <span className="text-xs text-gray-500 bg-white px-2 py-1 rounded">
            :{service.port}
          </span>
        )}
      </div>

      {/* 服務元數據 */}
      {service.metadata && (
        <div className="mb-3 space-y-1">
          {service.metadata.version && (
            <div className="text-xs text-gray-600">
              <span className="font-medium">版本:</span> {service.metadata.version}
            </div>
          )}
          {service.metadata.uptime !== undefined && (
            <div className="text-xs text-gray-600">
              <span className="font-medium">運行時間:</span> {Math.floor(service.metadata.uptime / 3600)}h {Math.floor((service.metadata.uptime % 3600) / 60)}m
            </div>
          )}
          {service.metadata.cpu_usage !== undefined && (
            <div className="text-xs text-gray-600">
              <span className="font-medium">CPU:</span> {service.metadata.cpu_usage.toFixed(1)}%
            </div>
          )}
          {service.metadata.memory_usage !== undefined && (
            <div className="text-xs text-gray-600">
              <span className="font-medium">內存:</span> {service.metadata.memory_usage}MB
            </div>
          )}
        </div>
      )}

      {/* 最後檢查時間 */}
      <div className="text-xs text-gray-500 mb-3">
        最後檢查: {formatTime(service.last_check_at)}
      </div>

      {/* 操作按鈕 */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onViewDetail(service.service_name)}
          className="flex-1 px-3 py-1.5 text-xs font-medium text-blue-600 bg-white border border-blue-200 rounded hover:bg-blue-50 transition-colors"
        >
          詳情
        </button>
        <button
          onClick={() => onViewLogs(service.service_name)}
          className="flex-1 px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-200 rounded hover:bg-gray-50 transition-colors"
        >
          日誌
        </button>
        {hasDashboard && onOpenDashboard && (
          <button
            onClick={() => onOpenDashboard(service.service_name)}
            className="flex-1 px-3 py-1.5 text-xs font-medium text-purple-600 bg-white border border-purple-200 rounded hover:bg-purple-50 transition-colors"
          >
            Dashboard
          </button>
        )}
      </div>
    </div>
  );
};

export default ServiceStatusCard;
