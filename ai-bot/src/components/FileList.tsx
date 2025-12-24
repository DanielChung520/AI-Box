/**
 * 代碼功能說明: 文件列表組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-13 18:28:38 (UTC+8)
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { File as FileIcon, Download, Trash2, Eye, RefreshCw, Search, Edit } from 'lucide-react';
import { getFileList, deleteFile, downloadFile, FileMetadata, getProcessingStatus } from '../lib/api';
import FilePreview from './FilePreview';

interface FileListProps {
  userId?: string;
  taskId?: string;
  onFileSelect?: (file: FileMetadata) => void;
  viewMode?: 'table' | 'card' | 'list';
  autoRefresh?: boolean; // 是否自動刷新
  refreshInterval?: number; // 刷新間隔（毫秒），默認5秒
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getStatusBadge = (status?: string, processingStatus?: string, processingData?: any) => {
  // 如果有處理狀態數據，使用更詳細的狀態
  if (processingData) {
    const overallStatus = processingData.status;
    const progress = processingData.progress || 0;

    if (overallStatus === 'completed') {
      return (
        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
          處理完成 ({progress}%)
        </span>
      );
    }
    if (overallStatus === 'processing' || overallStatus === 'in_progress') {
      return (
        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
          處理中 ({progress}%)
        </span>
      );
    }
    if (overallStatus === 'failed') {
      return <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded">處理失敗</span>;
    }
  }

  // 回退到基本狀態
  if (processingStatus === 'completed') {
    return <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">處理完成</span>;
  }
  if (processingStatus === 'processing') {
    return <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">處理中</span>;
  }
  if (status === 'uploaded') {
    return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">已上傳</span>;
  }
  return <span className="px-2 py-1 text-xs bg-gray-100 text-gray-800 rounded">未知</span>;
};

export default function FileList({ userId, taskId, onFileSelect, viewMode = 'table', autoRefresh = true, refreshInterval = 5000 }: FileListProps) {
  const navigate = useNavigate();
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<FileMetadata | null>(null);
  const [showPreview, setShowPreview] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalFiles, setTotalFiles] = useState(0);
  const [processingStatuses, setProcessingStatuses] = useState<Record<string, any>>({});
  const pageSize = 20;
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // 修改時間：2025-12-09 - 如果 taskId 是 'temp-workspace'，不傳遞 task_id 參數，避免 403 錯誤
      const response = await getFileList({
        user_id: userId,
        task_id: taskId && taskId !== 'temp-workspace' ? taskId : undefined,
        file_type: filterType || undefined,
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
        sort_by: 'upload_time',
        sort_order: 'desc',
      });

      if (response.success && response.data) {
        setFiles(response.data.files);
        setTotalFiles(response.data.total);
      } else {
        setError('獲取文件列表失敗');
      }
    } catch (err: any) {
      setError(err.message || '獲取文件列表失敗');
    } finally {
      setLoading(false);
    }
  }, [userId, taskId, filterType, currentPage]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // 自動刷新處理狀態
  useEffect(() => {
    if (!autoRefresh) return;

    const updateProcessingStatuses = async () => {
      // 只更新正在處理的文件狀態
      const processingFiles = files.filter(f =>
        f.processing_status === 'processing' ||
        f.status === 'uploaded' && !f.processing_status
      );

      for (const file of processingFiles) {
        try {
          const statusResponse = await getProcessingStatus(file.file_id);
          if (statusResponse.success && statusResponse.data) {
            setProcessingStatuses(prev => ({
              ...prev,
              [file.file_id]: statusResponse.data,
            }));

            // 如果處理完成，更新文件列表
            if (statusResponse.data.status === 'completed') {
              await loadFiles();
            }
          }
        } catch (err) {
          // 忽略錯誤，繼續更新其他文件
        }
      }
    };

    // 立即執行一次
    updateProcessingStatuses();

    // 設置定時器
    refreshTimerRef.current = setInterval(() => {
      updateProcessingStatuses();
      // 每30秒刷新一次文件列表（檢查是否有新文件）
      if (Math.random() < 0.1) { // 10%概率刷新列表
        loadFiles();
      }
    }, refreshInterval);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, [files, autoRefresh, refreshInterval, loadFiles]);

  const handleDelete = async (fileId: string) => {
    if (!confirm('確定要刪除此文件嗎？此操作無法撤銷。')) {
      return;
    }

    try {
      await deleteFile(fileId);
      await loadFiles();
    } catch (err: any) {
      alert(`刪除失敗: ${err.message}`);
    }
  };

  const handleDownload = async (file: FileMetadata) => {
    try {
      const blob = await downloadFile(file.file_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`下載失敗: ${err.message}`);
    }
  };

  const handlePreview = (file: FileMetadata) => {
    setSelectedFile(file);
    setShowPreview(true);
  };

  const handleEdit = (file: FileMetadata) => {
    // 檢查文件類型是否為 Markdown
    const fileName = file.filename.toLowerCase();
    const isMarkdown = fileName.endsWith('.md') || fileName.endsWith('.markdown');
    if (!isMarkdown) {
      alert('IEE 編輯器目前僅支持 Markdown 文件');
      return;
    }
    // 導航到 IEE 編輯器頁面
    navigate(`/iee-editor?fileId=${encodeURIComponent(file.file_id)}`);
  };

  const filteredFiles = files.filter(file => {
    if (searchQuery) {
      return file.filename.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const totalPages = Math.ceil(totalFiles / pageSize);

  if (viewMode === 'card') {
    return (
      <div className="p-4">
        <div className="mb-4 flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <input
              type="text"
              placeholder="搜索文件名..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg"
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border rounded-lg"
          >
            <option value="">所有類型</option>
            <option value="application/pdf">PDF</option>
            <option value="text/plain">文本</option>
            <option value="text/markdown">Markdown</option>
          </select>
          <button
            onClick={loadFiles}
            className="p-2 border rounded-lg hover:bg-gray-50"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {loading && <div className="text-center py-8">載入中...</div>}
        {error && <div className="text-red-500 py-4">{error}</div>}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFiles.map((file) => (
            <div
              key={file.file_id}
              className="border rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => onFileSelect?.(file)}
            >
              <div className="flex items-start justify-between mb-2">
                <FileIcon className="w-5 h-5 text-blue-500" />
                {getStatusBadge(file.status, file.processing_status, processingStatuses[file.file_id])}
              </div>
              <h3 className="font-medium truncate mb-1">{file.filename}</h3>
              <p className="text-sm text-gray-500 mb-2">
                {formatFileSize(file.file_size)} • {formatDate(file.upload_time)}
              </p>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handlePreview(file);
                  }}
                  className="flex-1 px-3 py-1 text-sm border rounded hover:bg-gray-50"
                >
                  <Eye className="w-4 h-4 inline mr-1" />
                  預覽
                </button>
                {(file.filename.toLowerCase().endsWith('.md') || file.filename.toLowerCase().endsWith('.markdown')) && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleEdit(file);
                    }}
                    className="flex-1 px-3 py-1 text-sm border rounded hover:bg-blue-50 text-blue-600"
                  >
                    <Edit className="w-4 h-4 inline mr-1" />
                    編輯
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDownload(file);
                  }}
                  className="flex-1 px-3 py-1 text-sm border rounded hover:bg-gray-50"
                >
                  <Download className="w-4 h-4 inline mr-1" />
                  下載
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(file.file_id);
                  }}
                  className="px-3 py-1 text-sm border rounded hover:bg-red-50 text-red-600"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>

        {totalPages > 1 && (
          <div className="mt-4 flex justify-center gap-2">
            <button
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="px-4 py-2 border rounded disabled:opacity-50"
            >
              上一頁
            </button>
            <span className="px-4 py-2">
              第 {currentPage} / {totalPages} 頁
            </span>
            <button
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="px-4 py-2 border rounded disabled:opacity-50"
            >
              下一頁
            </button>
          </div>
        )}

        {showPreview && selectedFile && (
          <FilePreview
            file={selectedFile}
            isOpen={showPreview}
            onClose={() => setShowPreview(false)}
          />
        )}
      </div>
    );
  }

  // Table view (default)
  return (
    <div className="p-4">
      <div className="mb-4 flex items-center gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="搜索文件名..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-4 py-2 border rounded-lg"
        >
          <option value="">所有類型</option>
          <option value="application/pdf">PDF</option>
          <option value="text/plain">文本</option>
          <option value="text/markdown">Markdown</option>
        </select>
        <button
          onClick={loadFiles}
          className="p-2 border rounded-lg hover:bg-gray-50"
          disabled={loading}
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {loading && <div className="text-center py-8">載入中...</div>}
      {error && <div className="text-red-500 py-4">{error}</div>}

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b">
              <th className="text-left p-2">文件名</th>
              <th className="text-left p-2">類型</th>
              <th className="text-left p-2">大小</th>
              <th className="text-left p-2">狀態</th>
              <th className="text-left p-2">上傳時間</th>
              <th className="text-left p-2">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredFiles.map((file) => (
              <tr key={file.file_id} className="border-b hover:bg-gray-50">
                <td className="p-2">
                  <div className="flex items-center gap-2">
                    <FileIcon className="w-4 h-4 text-blue-500" />
                    <span className="truncate max-w-xs">{file.filename}</span>
                  </div>
                </td>
                <td className="p-2 text-sm text-gray-600">{file.file_type}</td>
                <td className="p-2 text-sm text-gray-600">{formatFileSize(file.file_size)}</td>
                <td className="p-2">{getStatusBadge(file.status, file.processing_status, processingStatuses[file.file_id])}</td>
                <td className="p-2 text-sm text-gray-600">{formatDate(file.upload_time)}</td>
                <td className="p-2">
                  <div className="flex gap-2">
                    <button
                      onClick={() => handlePreview(file)}
                      className="p-1 hover:bg-gray-100 rounded"
                      title="預覽"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {(file.filename.toLowerCase().endsWith('.md') || file.filename.toLowerCase().endsWith('.markdown')) && (
                      <button
                        onClick={() => handleEdit(file)}
                        className="p-1 hover:bg-blue-100 rounded text-blue-600"
                        title="使用 IEE 編輯器打開"
                      >
                        <Edit className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDownload(file)}
                      className="p-1 hover:bg-gray-100 rounded"
                      title="下載"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(file.file_id)}
                      className="p-1 hover:bg-red-100 rounded text-red-600"
                      title="刪除"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-4 flex justify-center gap-2">
          <button
            onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            上一頁
          </button>
          <span className="px-4 py-2">
            第 {currentPage} / {totalPages} 頁
          </span>
          <button
            onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 border rounded disabled:opacity-50"
          >
            下一頁
          </button>
        </div>
      )}

      {showPreview && selectedFile && (
        <FilePreview
          file={selectedFile}
          isOpen={showPreview}
          onClose={() => setShowPreview(false)}
        />
      )}
    </div>
  );
}
