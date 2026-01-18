// 代碼功能說明: 系統設置頁面
// 創建日期: 2026-01-17 23:00 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-18 10:30 UTC+8

import React, { useState, useEffect } from 'react';
import { ArrowLeft, RefreshCw, Edit2, Check, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import {
  getSystemConfigs,
  updateSystemConfig,
  SystemConfig,
} from '@/lib/api';

type ConfigCategory = 'basic' | 'features' | 'performance' | 'security' | 'business';

interface ConfigEditorProps {
  config: SystemConfig;
  onSave: (scope: string, data: Record<string, any>) => Promise<void>;
}

const ConfigEditor: React.FC<ConfigEditorProps> = ({ config, onSave }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState(config.config_data);
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(config.scope, editedData);
      setIsEditing(false);
    } catch (error) {
      console.error('Failed to save config:', error);
      // 顯示錯誤提示
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditedData(config.config_data);
    setIsEditing(false);
  };

  // 根據值的類型渲染不同的輸入控件
  const renderConfigValue = (key: string, value: any) => {

    if (typeof value === 'boolean') {
      return (
        <div className="flex items-center space-x-2">
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={editedData[key]}
              onChange={(e) => setEditedData({ ...editedData, [key]: e.target.checked })}
              disabled={!isEditing}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700">
              {editedData[key] ? '啟用' : '禁用'}
            </span>
          </label>
        </div>
      );
    }

    if (typeof value === 'number') {
      return (
        <input
          type="number"
          value={editedData[key]}
          onChange={(e) => setEditedData({ ...editedData, [key]: Number(e.target.value) })}
          disabled={!isEditing}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      );
    }

    if (typeof value === 'string') {
      return (
        <input
          type="text"
          value={editedData[key]}
          onChange={(e) => setEditedData({ ...editedData, [key]: e.target.value })}
          disabled={!isEditing}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      );
    }

    if (typeof value === 'object') {
      return (
        <textarea
          value={JSON.stringify(editedData[key], null, 2)}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              setEditedData({ ...editedData, [key]: parsed });
            } catch (err) {
              // 忽略 JSON 解析錯誤
            }
          }}
          disabled={!isEditing}
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      );
    }

    return <span className="text-sm text-gray-700">{String(value)}</span>;
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{config.scope}</h3>
          {config.sub_scope && (
            <p className="text-sm text-gray-500">{config.sub_scope}</p>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {isEditing ? (
            <>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-3 py-1.5 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
              >
                <Check size={16} />
                <span>保存</span>
              </button>
              <button
                onClick={handleCancel}
                disabled={saving}
                className="px-3 py-1.5 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-1"
              >
                <X size={16} />
                <span>取消</span>
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="px-3 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors flex items-center space-x-1"
            >
              <Edit2 size={16} />
              <span>編輯</span>
            </button>
          )}
        </div>
      </div>

      <div className="space-y-4">
        {Object.entries(config.config_data).map(([key, value]) => (
          <div key={key} className="grid grid-cols-3 gap-4 items-start">
            <div className="col-span-1">
              <label className="block text-sm font-medium text-gray-700">
                {key}
              </label>
              <p className="text-xs text-gray-500 mt-1">
                類型: {typeof value}
              </p>
            </div>
            <div className="col-span-2">
              {renderConfigValue(key, value)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const SystemSettings: React.FC = () => {
  const navigate = useNavigate();
  const [activeCategory, setActiveCategory] = useState<ConfigCategory>('basic');
  const [configs, setConfigs] = useState<SystemConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  // 類別定義
  const categories = [
    { id: 'basic' as ConfigCategory, label: '基礎配置' },
    { id: 'features' as ConfigCategory, label: '功能開關' },
    { id: 'performance' as ConfigCategory, label: '性能參數' },
    { id: 'security' as ConfigCategory, label: '安全參數' },
    { id: 'business' as ConfigCategory, label: '業務參數' },
  ];

  // 載入配置
  const loadConfigs = async () => {
    setLoading(true);
    try {
      // 根據當前選擇的分類載入配置
      const categoryMap: Record<ConfigCategory, string> = {
        'basic': 'basic',
        'features': 'feature_flag',
        'performance': 'performance',
        'security': 'security',
        'business': 'business',
      };
      const category = categoryMap[activeCategory];
      const result = await getSystemConfigs(undefined, category);
      setConfigs(result);
    } catch (error) {
      console.error('Failed to load configs:', error);
      // 顯示錯誤提示
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, [activeCategory]); // 當分類改變時重新載入

  // 保存配置
  const handleSaveConfig = async (scope: string, data: Record<string, any>) => {
    try {
      await updateSystemConfig(scope, data);
      await loadConfigs(); // 重新載入配置
    } catch (error) {
      console.error('Failed to update config:', error);
      throw error;
    }
  };

  // 返回上一頁或主頁
  const handleBack = () => {
    navigate('/home');
  };

  // 過濾配置（因為已經按分類載入，這裡只需要按搜索詞過濾）
  const filteredConfigs = configs.filter((config) => {
    // 根據搜索詞過濾
    const searchMatch = !searchTerm ||
      config.scope.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (config.sub_scope && config.sub_scope.toLowerCase().includes(searchTerm.toLowerCase()));

    return searchMatch;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 頂部導航欄 */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBack}
              className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft size={20} />
              <span>返回</span>
            </button>
            <div className="h-6 w-px bg-gray-300"></div>
            <h1 className="text-2xl font-bold text-gray-900">系統設置</h1>
          </div>

          <button
            onClick={loadConfigs}
            disabled={loading}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            <span>刷新</span>
          </button>
        </div>

        {/* 類別標籤頁 */}
        <div className="flex space-x-4 overflow-x-auto">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => setActiveCategory(category.id)}
              className={`px-4 py-2 font-medium whitespace-nowrap transition-colors ${
                activeCategory === category.id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {category.label}
            </button>
          ))}
        </div>
      </div>

      {/* 內容區域 */}
      <div className="px-6 py-6">
        {/* 搜索框 */}
        <div className="mb-6">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="搜索配置項..."
            className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* 配置列表 */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="animate-spin text-gray-400" size={32} />
            <span className="ml-3 text-gray-600">載入中...</span>
          </div>
        ) : filteredConfigs.length === 0 ? (
          <div className="flex items-center justify-center h-64">
            <p className="text-gray-600">沒有找到配置項</p>
          </div>
        ) : (
          <div>
            {filteredConfigs.map((config) => (
              <ConfigEditor
                key={config.scope}
                config={config}
                onSave={handleSaveConfig}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemSettings;
