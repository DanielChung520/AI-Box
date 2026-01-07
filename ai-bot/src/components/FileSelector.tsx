/**
 * 代碼功能說明: 文件選擇器組件 - 用於選擇 Markdown 文件進行編輯
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { useState } from 'react';
import { FileText, X, AlertCircle, Loader2 } from 'lucide-react';
import { FileMetadata } from '../lib/api';
import FileSearchModal from './FileSearchModal';

interface FileSelectorProps {
  file: FileMetadata | null;
  onFileChange: (file: FileMetadata | null) => void;
  taskId?: string;
  userId?: string;
  fileTree?: any[];
}

/**
 * 檢查文件是否為 Markdown 文件
 */
function isMarkdownFile(file: FileMetadata): boolean {
  const markdownExtensions = ['.md', '.markdown'];
  const markdownMimeTypes = ['text/markdown', 'text/x-markdown'];

  // 檢查文件擴展名
  const fileName = file.filename.toLowerCase();
  const hasMarkdownExtension = markdownExtensions.some(ext => fileName.endsWith(ext));

  // 檢查 MIME 類型
  const hasMarkdownMimeType = file.file_type && markdownMimeTypes.includes(file.file_type.toLowerCase());

  return hasMarkdownExtension || hasMarkdownMimeType;
}

export default function FileSelector({
  file,
  onFileChange,
  taskId,
  userId,
  fileTree,
}: FileSelectorProps) {
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleFileSelect = async (fileId: string, fileName: string) => {
    setIsLoading(true);
    setError(null);

    try {
      // 從 fileTree 或其他來源獲取完整的 FileMetadata
      // 這裡我們需要找到對應的文件對象
      // 暫時使用 fileId 和 fileName 創建一個臨時對象進行驗證
      const tempFile: FileMetadata = {
        file_id: fileId,
        filename: fileName,
        file_type: 'text/markdown', // 默認假設為 markdown，實際應該從 API 獲取
        file_size: 0,
        tags: [],
        upload_time: new Date().toISOString(),
      };

      // 驗證文件類型
      if (!isMarkdownFile(tempFile)) {
        setError('僅支持 Markdown 文件（.md, .markdown）');
        setIsLoading(false);
        return;
      }

      // 清除錯誤並設置文件
      setError(null);

    // 如果 fileTree 存在，嘗試從中找到完整的文件對象
    if (fileTree) {
      const findFileInTree = (nodes: any[]): FileMetadata | null => {
        for (const node of nodes) {
          if (node.id === fileId) {
            // 構建 FileMetadata 對象
            return {
              file_id: node.id,
              filename: node.name,
              file_type: node.file_type || 'text/markdown',
              file_size: node.file_size || 0,
              tags: node.tags || [],
              upload_time: node.upload_time || new Date().toISOString(),
              user_id: node.user_id,
              task_id: node.task_id,
            };
          }
          if (node.children && node.children.length > 0) {
            const found = findFileInTree(node.children);
            if (found) return found;
          }
        }
        return null;
      };

      const foundFile = findFileInTree(fileTree);
      if (foundFile) {
        onFileChange(foundFile);
        setShowSearchModal(false);
        setIsLoading(false);
        return;
      }
    }

    // 如果找不到完整對象，使用臨時對象
    onFileChange(tempFile);
    setShowSearchModal(false);
    setIsLoading(false);
    } catch (err) {
      setError('文件選擇失敗，請重試');
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setError(null);
    onFileChange(null);
  };

  return (
    <div className="flex items-center gap-2">
      {file ? (
        <div className="flex items-center gap-2 px-2 py-1 bg-tertiary rounded-lg border border-primary">
          <FileText className="w-4 h-4 text-primary" />
          <span className="text-sm text-primary max-w-[200px] truncate">
            {file.filename}
          </span>
          <button
            onClick={handleClear}
            className="p-0.5 hover:bg-primary rounded transition-colors"
            aria-label="清除文件選擇"
          >
            <X className="w-3 h-3 text-tertiary" />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowSearchModal(true)}
          disabled={isLoading}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-tertiary hover:bg-primary rounded-lg border border-primary text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="選擇文件"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>載入中...</span>
            </>
          ) : (
            <>
              <FileText className="w-4 h-4" />
              <span>選擇文件</span>
            </>
          )}
        </button>
      )}

      {error && (
        <div className="flex items-center gap-1 px-2 py-1 bg-red-500/20 border border-red-500/50 rounded text-red-400 text-xs">
          <AlertCircle className="w-3 h-3" />
          <span>{error}</span>
        </div>
      )}

      <FileSearchModal
        isOpen={showSearchModal}
        onClose={() => {
          setShowSearchModal(false);
          setError(null);
        }}
        onFileSelect={handleFileSelect}
        taskId={taskId}
        userId={userId}
        fileTree={fileTree}
      />
    </div>
  );
}
