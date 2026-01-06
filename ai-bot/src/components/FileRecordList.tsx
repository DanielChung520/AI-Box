/**
 * 代碼功能說明: 文件記錄列表組件 - 顯示所有文件記錄，支持用戶篩選
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { useState, useEffect, useMemo } from 'react';
import { getFileList, FileMetadata } from '../lib/api';

interface FileRecordListProps {
  onFileSelect?: (file: FileMetadata) => void;
}

const formatDate = (dateString?: string): string => {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    return date.toLocaleString('zh-TW', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateString;
  }
};

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

export default function FileRecordList({ onFileSelect }: FileRecordListProps) {
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalFiles, setTotalFiles] = useState(0);
  const pageSize = 50;

  // 加載所有文件（不篩選用戶）
  const loadAllFiles = async () => {
    setLoading(true);
    setError(null);
    try {
      // 獲取大量文件（最多1000筆）
      const response = await getFileList({
        limit: 1000,
        offset: 0,
        sort_by: 'created_at',
        sort_order: 'desc',
      });
      
      if (response.success && response.data) {
        setFiles(response.data.files);
        setTotalFiles(response.data.total);
      } else {
        setError(response.message || '加載文件失敗');
      }
    } catch (err) {
      console.error('Failed to load files:', err);
      setError('加載文件失敗');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllFiles();
  }, []);

  // 提取所有唯一的用戶ID
  const uniqueUserIds = useMemo(() => {
    const userIds = new Set<string>();
    files.forEach(file => {
      if (file.user_id) {
        userIds.add(file.user_id);
      }
    });
    return Array.from(userIds).sort();
  }, [files]);

  // 根據選中的用戶篩選文件
  const filteredFiles = useMemo(() => {
    if (selectedUserId === 'all') {
      return files;
    }
    return files.filter(file => file.user_id === selectedUserId);
  }, [files, selectedUserId]);

  // 分頁處理
  const paginatedFiles = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return filteredFiles.slice(start, end);
  }, [filteredFiles, currentPage]);

  const totalPages = Math.ceil(filteredFiles.length / pageSize);

  // 獲取文件版本（從 custom_metadata 中獲取，如果沒有則顯示 N/A）
  const getFileVersion = (file: FileMetadata): string => {
    if (file.custom_metadata && typeof file.custom_metadata === 'object') {
      const version = (file.custom_metadata as any).version;
      if (version) {
        return String(version);
      }
    }
    return 'N/A';
  };

  // 獲取備註（優先使用 description，如果沒有則從 custom_metadata 獲取）
  const getFileNote = (file: FileMetadata): string => {
    if (file.description) {
      return file.description;
    }
    if (file.custom_metadata && typeof file.custom_metadata === 'object') {
      const note = (file.custom_metadata as any).note || (file.custom_metadata as any).备注;
      if (note) {
        return String(note);
      }
    }
    return '-';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">加載中...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 篩選器 */}
      <div className="p-4 border-b bg-white">
        <div className="flex items-center gap-4">
          <label className="text-sm font-medium text-gray-700">篩選創建用戶：</label>
          <select
            value={selectedUserId}
            onChange={(e) => {
              setSelectedUserId(e.target.value);
              setCurrentPage(1); // 重置到第一頁
            }}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">全部用戶</option>
            {uniqueUserIds.map(userId => (
              <option key={userId} value={userId}>
                {userId}
              </option>
            ))}
          </select>
          <div className="text-sm text-gray-500">
            共 {filteredFiles.length} 筆文件記錄
          </div>
        </div>
      </div>

      {/* 文件記錄表格 */}
      <div className="flex-1 overflow-auto">
        <table className="w-full border-collapse">
          <thead className="bg-gray-50 sticky top-0">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">文件名稱</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">說明</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">版本</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">創建時間</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">最近更新時間</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">備註</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">文件大小</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">創建用戶</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedFiles.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                  沒有找到文件記錄
                </td>
              </tr>
            ) : (
              paginatedFiles.map((file) => (
                <tr
                  key={file.file_id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => onFileSelect?.(file)}
                >
                  <td className="px-4 py-3 text-sm text-gray-900">
                    <div className="font-medium">{file.filename}</div>
                    <div className="text-xs text-gray-500">{file.file_type}</div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {file.description || '-'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {getFileVersion(file)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {formatDate(file.created_at || file.upload_time)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {formatDate(file.updated_at)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    <div className="max-w-xs truncate" title={getFileNote(file)}>
                      {getFileNote(file)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {formatFileSize(file.file_size)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {file.user_id || '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* 分頁器 */}
      {totalPages > 1 && (
        <div className="p-4 border-t bg-white flex items-center justify-between">
          <div className="text-sm text-gray-500">
            顯示第 {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, filteredFiles.length)} 筆，共 {filteredFiles.length} 筆
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="px-3 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              上一頁
            </button>
            <span className="text-sm text-gray-700">
              第 {currentPage} / {totalPages} 頁
            </span>
            <button
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              className="px-3 py-1 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              下一頁
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

