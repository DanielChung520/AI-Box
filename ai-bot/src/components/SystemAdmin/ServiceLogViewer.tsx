// 代碼功能說明: 服務日誌查看器組件
// 創建日期: 2026-01-17 22:35 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 12:15 UTC+8

import React, { useState, useEffect } from 'react';
import { X, Maximize2, Minimize2, Search, RefreshCw } from 'lucide-react';
import { getServiceLogs, ServiceLog, ServiceLogFilters } from '@/lib/api';

interface ServiceLogViewerProps {
  serviceName: string;
  onClose: () => void;
}

const ServiceLogViewer: React.FC<ServiceLogViewerProps> = ({ serviceName, onClose }) => {
  const [logs, setLogs] = useState<ServiceLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [filters, setFilters] = useState<ServiceLogFilters>({
    log_level: 'ALL',
    limit: 100,
  });
  const [keyword, setKeyword] = useState('');
  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');

  // 載入日誌
  const loadLogs = async () => {
    setLoading(true);
    try {
      const filterParams: ServiceLogFilters = {
        ...filters,
        keyword: keyword || undefined,
        start_time: startTime || undefined,
        end_time: endTime || undefined,
      };
      const result = await getServiceLogs(serviceName, filterParams);
      // 修改時間：2026-01-18 - 確保 result 是數組，如果是 API 響應對象則提取 logs
      if (Array.isArray(result)) {
        setLogs(result);
      } else if (result && typeof result === 'object' && 'logs' in result) {
        setLogs(result.logs || []);
      } else {
        setLogs([]);
      }
    } catch (error) {
      console.error('Failed to load logs:', error);
      setLogs([]); // 出錯時設置為空數組
      // 顯示錯誤提示 (可以使用 toast 或其他通知組件)
    } finally {
      setLoading(false);
    }
  };

  // 初始載入
  useEffect(() => {
    loadLogs();
  }, [serviceName]);

  // 搜索日誌
  const handleSearch = () => {
    loadLogs();
  };

  // 切換全屏
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // 獲取日誌級別的顏色
  const getLogLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'DEBUG':
        return 'text-gray-600';
      case 'INFO':
        return 'text-blue-600';
      case 'WARNING':
        return 'text-yellow-600';
      case 'ERROR':
        return 'text-red-600';
      case 'CRITICAL':
        return 'text-red-800 font-bold';
      default:
        return 'text-gray-700';
    }
  };

  // 獲取當前日期時間 (用於日期選擇器默認值)
  const getDefaultDateTime = (hoursAgo: number = 0) => {
    const date = new Date();
    date.setHours(date.getHours() - hoursAgo);
    return date.toISOString().slice(0, 16);
  };

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 ${isFullscreen ? 'p-0' : 'p-4'}`}>
      <div className={`bg-white rounded-lg shadow-xl flex flex-col ${isFullscreen ? 'w-full h-full rounded-none' : 'w-full max-w-4xl h-5/6'}`}>
        {/* 標題欄 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-xl font-semibold text-gray-900">
            服務日誌: {serviceName}
          </h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={toggleFullscreen}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
              title={isFullscreen ? '退出全屏' : '全屏'}
            >
              {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
            </button>
            <button
              onClick={onClose}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
              title="關閉"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* 過濾條件 */}
        <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 space-y-3">
          {/* 時間範圍 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                開始時間
              </label>
              <input
                type="datetime-local"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="開始時間"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                結束時間
              </label>
              <input
                type="datetime-local"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="結束時間"
              />
            </div>
          </div>

          {/* 日誌級別和關鍵字搜索 */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                日誌級別
              </label>
              <select
                value={filters.log_level}
                onChange={(e) => setFilters({ ...filters, log_level: e.target.value as any })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="ALL">全部</option>
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                關鍵字搜索
              </label>
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="搜索關鍵字..."
                />
                <button
                  onClick={handleSearch}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
                >
                  <Search size={16} />
                  <span>搜索</span>
                </button>
                <button
                  onClick={loadLogs}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="重新載入"
                >
                  <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 日誌內容 */}
        <div className="flex-1 overflow-y-auto px-6 py-4 bg-gray-900 font-mono text-sm">
          {loading ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              <RefreshCw className="animate-spin mr-2" size={20} />
              載入中...
            </div>
          ) : logs.length === 0 ? (
            <div className="flex items-center justify-center h-full text-gray-400">
              沒有找到日誌記錄
            </div>
          ) : (
            <div className="space-y-1">
              {logs.map((log, index) => (
                <div key={index} className="text-gray-100 hover:bg-gray-800 px-2 py-1 rounded">
                  <span className="text-gray-500">{new Date(log.timestamp).toLocaleString('zh-TW')}</span>
                  {' '}
                  <span className={`font-semibold ${getLogLevelColor(log.log_level)}`}>
                    [{log.log_level}]
                  </span>
                  {' '}
                  <span>{log.message}</span>
                  {log.metadata && Object.keys(log.metadata).length > 0 && (
                    <div className="text-gray-400 text-xs ml-4 mt-1">
                      {JSON.stringify(log.metadata, null, 2)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 底部狀態欄 */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 text-sm text-gray-600">
          共 {logs.length} 條日誌
        </div>
      </div>
    </div>
  );
};

export default ServiceLogViewer;
