/**
 * 代碼功能說明: 文件記錄 Modal 組件 - 顯示所有文件記錄，支持用戶篩選
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { useState, useEffect, useMemo } from 'react';
import { X } from 'lucide-react';
import { getFileList, FileMetadata, getUserTask } from '../lib/api';

interface FileRecordModalProps {
  isOpen: boolean;
  onClose: () => void;
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

export default function FileRecordModal({ isOpen, onClose, onFileSelect }: FileRecordModalProps) {
  const [files, setFiles] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedUserId, setSelectedUserId] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalFiles, setTotalFiles] = useState(0);
  const [taskNames, setTaskNames] = useState<Record<string, string>>({}); // 修改時間：2026-01-06 - 任務ID到任務名稱的映射
  const pageSize = 50;

  // 修改時間：2026-01-06 - 加載任務名稱（批量獲取，限制並發數）
  const loadTaskNames = async (filesList: FileMetadata[]) => {
    // 收集所有唯一的 task_id
    const taskIds = new Set<string>();
    filesList.forEach(file => {
      if (file.task_id) {
        taskIds.add(file.task_id);
      }
    });

    if (taskIds.size === 0) {
      return;
    }

    // 批量獲取任務信息（限制並發數為 5，避免過多請求）
    const taskNameMap: Record<string, string> = {};
    const taskIdArray = Array.from(taskIds);
    const batchSize = 5; // 每次並發處理 5 個任務

    for (let i = 0; i < taskIdArray.length; i += batchSize) {
      const batch = taskIdArray.slice(i, i + batchSize);
      const batchPromises = batch.map(async (taskId) => {
        try {
          const response = await getUserTask(taskId);
          if (response.success && response.data) {
            taskNameMap[taskId] = response.data.title || taskId;
          } else {
            taskNameMap[taskId] = taskId; // 如果獲取失敗，使用 task_id
          }
        } catch (err) {
          console.error(`[FileRecordModal] 獲取任務 ${taskId} 失敗:`, err);
          taskNameMap[taskId] = taskId; // 如果獲取失敗，使用 task_id
        }
      });

      await Promise.all(batchPromises);
      // 更新狀態，讓用戶可以看到已加載的任務名稱
      setTaskNames({ ...taskNameMap });
    }
  };

  // 加載所有文件（不篩選用戶）
  const loadAllFiles = async () => {
    if (!isOpen) return;
    
    setLoading(true);
    setError(null);
    try {
      console.log('[FileRecordModal] 開始加載文件列表...');
      // 使用 /files 端點獲取文件列表
      // 注意：該端點默認返回當前用戶的文件，如果需要查看所有文件需要管理員權限
      // sort_by 使用 'upload_time'（API 默認使用此字段）
      const response = await getFileList({
        limit: 1000,
        offset: 0,
        sort_by: 'upload_time', // 使用 upload_time 作為排序字段
        sort_order: 'desc',
        view_all_files: true, // 修改時間：2026-01-06 - 請求查看所有文件（需要管理員權限）
      });
      
      console.log('[FileRecordModal] API 響應:', {
        success: response.success,
        hasData: !!response.data,
        filesCount: response.data?.files?.length || 0,
        total: response.data?.total || 0,
        message: response.message,
        fullResponse: response,
      });
      
      if (response.success && response.data) {
        const filesArray = response.data.files || [];
        console.log('[FileRecordModal] 文件數量:', filesArray.length);
        console.log('[FileRecordModal] 前3個文件示例:', filesArray.slice(0, 3));
        
        if (filesArray.length === 0) {
          setError('沒有找到文件記錄（可能是權限問題或數據庫中沒有文件）');
        } else {
          setFiles(filesArray);
          setTotalFiles(response.data.total || filesArray.length);
          
          // 修改時間：2026-01-06 - 文件加載完成後，加載任務名稱
          loadTaskNames(filesArray);
        }
      } else {
        const errorMsg = response.message || '加載文件失敗';
        console.error('[FileRecordModal] 加載失敗:', errorMsg, response);
        setError(errorMsg);
      }
    } catch (err) {
      console.error('[FileRecordModal] 加載文件異常:', err);
      setError(`加載文件失敗: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadAllFiles();
    }
  }, [isOpen]);

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

  // 獲取訪問級別
  const getAccessLevel = (file: FileMetadata): string => {
    return file.access_control?.access_level || '-';
  };

  // 獲取授權組織
  const getAuthorizedOrganizations = (file: FileMetadata): string => {
    const orgs = file.access_control?.authorized_organizations;
    if (orgs && orgs.length > 0) {
      return orgs.join(', ');
    }
    return '-';
  };

  // 獲取數據分類
  const getDataClassification = (file: FileMetadata): string => {
    return file.data_classification || file.access_control?.data_classification || '-';
  };

  // 獲取敏感性標籤
  const getSensitivityLabels = (file: FileMetadata): string => {
    const labels = file.sensitivity_labels || file.access_control?.sensitivity_labels;
    if (labels && labels.length > 0) {
      return labels.join(', ');
    }
    return '-';
  };

  // 處理 ESC 鍵關閉
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => {
        document.removeEventListener('keydown', handleEscape);
      };
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition" onClick={onClose}>
      <div 
        className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-[95vw] h-[90vh] flex flex-col theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal 標題 */}
        <div className="p-4 border-b border-primary flex items-center justify-between">
          <h2 className="text-lg font-semibold text-primary theme-transition">文件記錄</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-tertiary transition-colors"
            aria-label="關閉"
          >
            <X className="w-5 h-5 text-primary" />
          </button>
        </div>

        {/* 篩選器 */}
        <div className="p-4 border-b border-primary bg-white">
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
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">加載中...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-red-500">{error}</div>
            </div>
          ) : (
            <table className="w-full border-collapse">
              <thead className="bg-gray-50 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">文件名稱</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">說明</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">版本</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">所屬任務</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">訪問級別</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">授權組織</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">數據分類</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase border-b">敏感性標籤</th>
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
                    <td colSpan={13} className="px-4 py-8 text-center text-gray-500">
                      沒有找到文件記錄
                    </td>
                  </tr>
                ) : (
                  paginatedFiles.map((file) => (
                    <tr
                      key={file.file_id}
                      className="hover:bg-blue-100 hover:shadow-lg hover:scale-[1.01] cursor-pointer transition-all duration-200 border-b border-gray-100 group"
                      onClick={() => {
                        onFileSelect?.(file);
                        // 修改時間：2026-01-06 - 點擊文件時不關閉 Modal
                      }}
                    >
                      <td className="px-4 py-3 text-sm text-gray-900 group-hover:text-blue-700">
                        <div className="font-medium">{file.filename}</div>
                        <div className="text-xs text-gray-500 group-hover:text-blue-600">{file.file_type}</div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {file.description || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {getFileVersion(file)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {file.task_id ? (taskNames[file.task_id] || file.task_id) : '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                          {getAccessLevel(file)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {getAuthorizedOrganizations(file)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                          {getDataClassification(file)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {getSensitivityLabels(file)}
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
          )}
        </div>

        {/* 分頁器 */}
        {totalPages > 1 && (
          <div className="p-4 border-t border-primary bg-white flex items-center justify-between">
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
    </div>
  );
}

