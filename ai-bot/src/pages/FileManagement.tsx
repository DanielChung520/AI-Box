/**
 * 代碼功能說明: 文件管理頁面
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 */

import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Search, Grid, List } from 'lucide-react';
import FileList from '../components/FileList';
import FileSearch from '../components/FileSearch';
import FileTree from '../components/FileTree';
import { FileMetadata } from '../lib/api';

export default function FileManagement() {
  const navigate = useNavigate();
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table');
  const [showSearch, setShowSearch] = useState(false);
  const [selectedFile, setSelectedFile] = useState<FileMetadata | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>('temp-workspace'); // 默認選中任務工作區
  const fileListRef = useRef<{ refresh: () => void } | null>(null);

  // 從 localStorage 獲取當前用戶ID（實際應用中應該從認證上下文獲取）
  const userId = localStorage.getItem('user_id') || undefined;

  // 監聽文件上傳完成事件
  useEffect(() => {
    const handleFileUploaded = () => {
      // 觸發文件列表刷新
      setRefreshKey(prev => prev + 1);
    };

    window.addEventListener('fileUploaded', handleFileUploaded as EventListener);
    return () => {
      window.removeEventListener('fileUploaded', handleFileUploaded as EventListener);
    };
  }, []);

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <div className="border-b bg-white p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-blue-500" />
            <h1 className="text-2xl font-semibold">文件管理</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowSearch(!showSearch)}
              className={`px-4 py-2 border rounded-lg flex items-center gap-2 ${
                showSearch ? 'bg-blue-50 border-blue-500' : ''
              }`}
            >
              <Search className="w-4 h-4" />
              搜索
            </button>
            <div className="flex border rounded-lg">
              <button
                onClick={() => setViewMode('table')}
                className={`p-2 ${viewMode === 'table' ? 'bg-blue-50' : ''}`}
                title="表格視圖"
              >
                <List className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('card')}
                className={`p-2 ${viewMode === 'card' ? 'bg-blue-50' : ''}`}
                title="卡片視圖"
              >
                <Grid className="w-4 h-4" />
              </button>
            </div>
            <button
              onClick={() => navigate('/')}
              className="px-4 py-2 border rounded-lg hover:bg-gray-50"
            >
              返回首頁
            </button>
          </div>
        </div>

        {/* Search Panel */}
        {showSearch && (
          <div className="mt-4 border rounded-lg bg-gray-50">
            <FileSearch
              userId={userId}
              onFileSelect={(file) => {
                setSelectedFile(file);
                setShowSearch(false);
              }}
            />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto flex">
        {/* 文件樹側邊欄 */}
        <div className="w-64 border-r border-gray-200 bg-white flex-shrink-0">
          <FileTree
            userId={userId}
            selectedTaskId={selectedTaskId}
            onTaskSelect={(taskId) => {
              setSelectedTaskId(taskId);
              // 切換工作區時刷新文件列表
              setRefreshKey(prev => prev + 1);
            }}
          />
        </div>

        {/* 文件列表主區域 */}
        <div className="flex-1 overflow-auto">
          <FileList
            key={refreshKey}
            userId={userId}
            taskId={selectedTaskId || undefined}
            viewMode={viewMode}
            onFileSelect={(file) => {
              setSelectedFile(file);
            }}
            autoRefresh={true}
          />
        </div>
      </div>
    </div>
  );
}
