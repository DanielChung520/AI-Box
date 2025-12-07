/**
 * 代碼功能說明: 文件庫選擇對話框組件
 * 創建日期: 2025-12-07
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-07
 *
 * 功能說明:
 * - 顯示文件庫中的文件列表
 * - 支持文件多選
 * - 支持文件搜尋
 * - 支持上傳選中的文件到當前任務
 */

import React, { useState, useEffect } from 'react';
import { X, Search, File as FileIcon, Check } from 'lucide-react';
import { searchLibrary, LibrarySearchResponse } from '../lib/api';

interface FileLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (fileIds: string[]) => void;
  userId?: string;
}

interface LibraryFile {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
}

export default function FileLibraryModal({
  isOpen,
  onClose,
  onSelect,
  userId,
}: FileLibraryModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [files, setFiles] = useState<LibraryFile[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // 搜尋文件庫
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setError('請輸入搜尋關鍵詞');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response: LibrarySearchResponse = await searchLibrary({
        query: searchQuery.trim(),
        page: 1,
        limit: 20,
      });

      if (response.success && response.data) {
        setFiles(response.data.files);
        setTotalPages(response.data.total_pages);
        setPage(1);
      } else {
        setError(response.message || '搜尋失敗');
      }
    } catch (err: any) {
      setError(err.message || '搜尋失敗');
    } finally {
      setLoading(false);
    }
  };

  // 處理文件選擇
  const handleFileToggle = (fileId: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  // 處理確認選擇
  const handleConfirm = () => {
    if (selectedFiles.size === 0) {
      setError('請至少選擇一個文件');
      return;
    }
    onSelect(Array.from(selectedFiles));
    handleClose();
  };

  // 處理關閉
  const handleClose = () => {
    setSearchQuery('');
    setFiles([]);
    setSelectedFiles(new Set());
    setError(null);
    setPage(1);
    onClose();
  };

  // 處理 Enter 鍵搜尋
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
      <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-2xl max-h-[80vh] flex flex-col theme-transition">
        {/* 標題欄 */}
        <div className="flex items-center justify-between p-4 border-b border-primary">
          <h2 className="text-lg font-semibold text-primary">從文件庫選擇文件</h2>
          <button
            onClick={handleClose}
            className="p-1 rounded hover:bg-tertiary text-tertiary hover:text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 搜尋欄 */}
        <div className="p-4 border-b border-primary">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-tertiary" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="搜尋文件名..."
                className="w-full pl-10 pr-4 py-2 bg-tertiary border border-primary rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading || !searchQuery.trim()}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? '搜尋中...' : '搜尋'}
            </button>
          </div>
          {error && (
            <div className="mt-2 text-sm text-red-500">{error}</div>
          )}
        </div>

        {/* 文件列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {files.length === 0 && !loading && (
            <div className="text-center text-tertiary py-8">
              {searchQuery ? '沒有找到文件，請嘗試其他關鍵詞' : '請輸入關鍵詞搜尋文件庫'}
            </div>
          )}
          {loading && (
            <div className="text-center text-tertiary py-8">搜尋中...</div>
          )}
          {files.length > 0 && (
            <div className="space-y-2">
              {files.map((file) => (
                <div
                  key={file.file_id}
                  onClick={() => handleFileToggle(file.file_id)}
                  className={`flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors ${
                    selectedFiles.has(file.file_id)
                      ? 'bg-blue-500/20 border-2 border-blue-500'
                      : 'bg-tertiary hover:bg-hover border-2 border-transparent'
                  }`}
                >
                  <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                    selectedFiles.has(file.file_id)
                      ? 'bg-blue-500 border-blue-500'
                      : 'border-primary'
                  }`}>
                    {selectedFiles.has(file.file_id) && (
                      <Check className="w-3 h-3 text-white" />
                    )}
                  </div>
                  <FileIcon className="w-5 h-5 text-tertiary" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-primary">{file.filename}</div>
                    <div className="text-xs text-tertiary">
                      {file.file_type} • {(file.file_size / 1024).toFixed(2)} KB
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 底部操作欄 */}
        <div className="flex items-center justify-between p-4 border-t border-primary">
          <div className="text-sm text-tertiary">
            已選擇 {selectedFiles.size} 個文件
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleClose}
              className="px-4 py-2 bg-tertiary text-primary rounded-lg hover:bg-hover transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={selectedFiles.size === 0}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              確認選擇
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
