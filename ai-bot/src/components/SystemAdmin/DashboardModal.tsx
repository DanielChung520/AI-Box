// 代碼功能說明: Dashboard 浮動視窗組件
// 創建日期: 2026-01-17 22:40 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-17 22:40 UTC+8

import React, { useState } from 'react';
import { X, Maximize2, Minimize2, ExternalLink } from 'lucide-react';

interface DashboardModalProps {
  serviceName: string;
  onClose: () => void;
}

const DashboardModal: React.FC<DashboardModalProps> = ({ serviceName, onClose }) => {
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 根據服務名稱獲取 Dashboard URL
  const getDashboardUrl = () => {
    const serviceLower = serviceName.toLowerCase();

    if (serviceLower === 'arangodb') {
      return 'http://localhost:8529';
    } else if (serviceLower === 'rq') {
      return 'http://localhost:9181';
    } else if (serviceLower === 'seaweedfs') {
      return 'http://localhost:9333'; // SeaweedFS Master UI
    }

    return '';
  };

  const dashboardUrl = getDashboardUrl();

  // 切換全屏
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  // 在新標籤頁打開
  const openInNewTab = () => {
    if (dashboardUrl) {
      window.open(dashboardUrl, '_blank', 'noopener,noreferrer');
    }
  };

  // 如果沒有 Dashboard URL,顯示錯誤
  if (!dashboardUrl) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
        <div className="bg-white rounded-lg shadow-xl p-6 max-w-md">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Dashboard 不可用</h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
            >
              <X size={20} />
            </button>
          </div>
          <p className="text-gray-600">
            該服務 ({serviceName}) 沒有可用的 Dashboard。
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 ${isFullscreen ? 'p-0' : 'p-4'}`}>
      <div className={`bg-white rounded-lg shadow-xl flex flex-col ${isFullscreen ? 'w-full h-full rounded-none' : 'w-full max-w-6xl h-5/6'}`}>
        {/* 標題欄 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 bg-gray-50">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-semibold text-gray-900">
              {serviceName} Dashboard
            </h2>
            <span className="text-sm text-gray-500">
              {dashboardUrl}
            </span>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={openInNewTab}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors"
              title="在新標籤頁打開"
            >
              <ExternalLink size={20} />
            </button>
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

        {/* Iframe 內容 */}
        <div className="flex-1 relative">
          <iframe
            src={dashboardUrl}
            className="absolute inset-0 w-full h-full border-0"
            title={`${serviceName} Dashboard`}
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
          />
        </div>

        {/* 底部提示 */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 text-sm text-gray-600">
          <div className="flex items-center justify-between">
            <span>
              提示: 如果 Dashboard 無法載入,請檢查服務是否正常運行,或點擊右上角按鈕在新標籤頁打開。
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardModal;
