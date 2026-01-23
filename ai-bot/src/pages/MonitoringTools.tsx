// 代碼功能說明: 監控工具頁面更新 - 直接代理方案
// 創建日期: 2026-01-18 14:30 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 14:30 UTC+8

import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { AuthContext } from '@/contexts/authContext';
import { useLanguage } from '@/contexts/languageContext';

const MonitoringTools: React.FC = () => {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const { currentUser } = useContext(AuthContext);

  const handleBack = () => {
    navigate('/home');
  };

  const handleOpenGrafana = () => {
    // 通過 Cloudflare Tunnel 打開 Grafana (gfn.k84.org)
    window.open('https://gfn.k84.org', '_blank');
  };

  const handleOpenPrometheus = () => {
    window.open('https://pmt.k84.org', '_blank');
  };

  const hasSystemAdminAccess = currentUser?.roles?.includes('system_admin') || false;

  const tools = [
    {
      id: 'grafana',
      name: 'Grafana',
      description: '監控儀表板和數據可視化',
      icon: '📊',
      color: 'from-orange-400 to-red-500',
      action: handleOpenGrafana,
    },
    {
      id: 'prometheus',
      name: 'Prometheus',
      description: '指標查詢和數據存儲',
      icon: '📈',
      color: 'from-blue-400 to-indigo-500',
      action: handleOpenPrometheus,
    },
  ];

  if (!hasSystemAdminAccess) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              <ArrowLeft size={20} />
              <span>返回</span>
            </button>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">監控工具</h1>
          </div>
        </div>

        <div className="max-w-6xl mx-auto px-6 py-12">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 mb-6">
            <div className="flex items-start space-x-3">
              <div className="text-red-600 dark:text-red-400 text-2xl">⚠️</div>
              <div>
                <h3 className="text-lg font-semibold text-red-900 dark:text-red-100 mb-2">
                  權限不足
                </h3>
                <p className="text-red-800 dark:text-red-200">
                  您的賬戶沒有 system_admin 角色，無法訪問監控工具。
                  <br />
                  請聯系系統管理員授予相應權限。
                </p>
              </div>
            </div>
          </div>

          <div className="text-center mb-8">
            <p className="text-gray-600 dark:text-gray-400">
              <button
                onClick={() => navigate('/admin/settings')}
                className="text-blue-600 dark:text-blue-400 hover:underline"
              >
                返回設置
              </button>
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 opacity-50">
            {tools.map((tool) => (
              <button
                key={tool.id}
                disabled
                className="group relative overflow-hidden rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 bg-gradient-to-br dark:from-gray-800 dark:to-gray-900"
                style={{
                  background: `linear-gradient(135deg, ${tool.color})`,
                }}
              >
                <div className="absolute inset-0 bg-black opacity-0 group-hover:opacity-10 transition-opacity duration-300"></div>
                <div className="relative p-8">
                  <div className="text-6xl mb-6 opacity-50">{tool.icon}</div>
                  <h3 className="text-3xl font-bold text-white mb-3">
                    {tool.name}
                  </h3>
                  <p className="text-white text-opacity-90 text-lg">
                    {tool.description}
                  </p>
                  <div className="mt-6 flex items-center text-white font-semibold opacity-75">
                    <span>訪問</span>
                    <ArrowLeft className="ml-2 rotate-180" size={20} />
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
      {/* 頂部導航欄 */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={handleBack}
            className="flex items-center space-x-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
            <span>返回</span>
          </button>
          <div className="h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">監控工具</h1>
        </div>
      </div>

      {/* 主內容 */}
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            選擇監控工具
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            僅系統管理員（system_admin）可以訪問監控工具
          </p>
        </div>

        {/* 工具卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {tools.map((tool) => (
            <button
              key={tool.id}
              onClick={tool.action}
              disabled={!hasSystemAdminAccess}
              className={`group relative overflow-hidden rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 ${
                hasSystemAdminAccess
                  ? ''
                  : 'opacity-50 cursor-not-allowed'
              }`}
              style={{
                background: `linear-gradient(135deg, ${tool.color})`,
              }}
            >
              <div
                className={`absolute inset-0 bg-black transition-opacity duration-300 ${
                  hasSystemAdminAccess ? '' : 'group-hover:opacity-10'
                }`}
              ></div>
              <div className="relative p-8">
                <div className="text-6xl mb-6">{tool.icon}</div>
                <h3 className="text-3xl font-bold text-white mb-3">
                  {tool.name}
                </h3>
                <p className="text-white text-opacity-90 text-lg">
                  {tool.description}
                </p>
                <div className="mt-6 flex items-center text-white font-semibold">
                  <span>訪問</span>
                  <ArrowLeft className="ml-2 rotate-180" size={20} />
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* 權限說明 */}
        <div className="mt-12 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
          <div className="flex items-start space-x-3">
            <div className="text-yellow-600 dark:text-yellow-400 text-2xl">⚠️</div>
            <div>
              <h3 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100 mb-2">
                權限說明
              </h3>
              <p className="text-yellow-800 dark:text-yellow-200">
                {hasSystemAdminAccess ? (
                  "您擁有 system_admin 角色，可以訪問監控工具。"
                ) : (
                  "只有擁有 system_admin 角色的用戶才能訪問監控工具。請聯繫系統管理員。"
                )}
              </p>
            </div>
          </div>
        </div>

        {/* 使用說明 */}
        <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-4">
            使用說明
          </h3>
          <ul className="list-disc list-inside space-y-2 text-blue-800 dark:text-blue-200">
            <li>點擊訪問按鈕會在新標籤頁中打開對應的監控工具</li>
            <li>所有訪問受權限保護，需要 system_admin 角色</li>
            <li>Grafana 密碼：<code className="bg-blue-200 dark:bg-blue-800 px-2 py-1 rounded">
              admin / 86b1d1c265ebbd3d827cd7b5ded6704d
            </code></li>
            <li>Prometheus 無法認證，建議限制內網訪問</li>
          </ul>
        </div>

        {/* 權限管理建議 */}
        <div className="mt-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-4">
            權限管理建議
          </h3>
          <p className="text-green-800 dark:text-green-200">
            要授予用戶 system_admin 角色：
          </p>
          <ul className="list-decimal list-inside space-y-2 text-green-800 dark:text-green-200">
            <li>登入 AI-Box 管理員</li>
            <li>導航到「用戶/安全群組設置」</li>
            <li>找到目標用戶</li>
            <li>在角色中添加「system_admin」角色</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default MonitoringTools;
