// 代碼功能說明: Review 模式對話框組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useState, useEffect, useCallback } from 'react';
import { X } from 'lucide-react';
import MonacoDiffEditor from './MonacoDiffEditor';
import ChangeNavigation from './ChangeNavigation';
import type { editor } from 'monaco-editor';
import { listDocVersions, previewFile } from '../../lib/api';
import { toast } from 'sonner';

export interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileId: string;
  modifiedContent: string;
  onCommit?: () => void;
}

export default function ReviewModal({
  isOpen,
  onClose,
  fileId,
  modifiedContent,
  onCommit,
}: ReviewModalProps) {
  const [originalContent, setOriginalContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [diffEditor, setDiffEditor] = useState<editor.IStandaloneDiffEditor | null>(null);
  const [currentChangeIndex, setCurrentChangeIndex] = useState<number>(0);
  const [totalChanges, setTotalChanges] = useState<number>(0);

  // 加載原始版本內容
  const loadOriginalVersion = useCallback(async () => {
    if (!fileId) return;

    setIsLoading(true);
    try {
      // 獲取版本列表
      const versionsResponse = await listDocVersions(fileId);

      if (!versionsResponse.success || !versionsResponse.data) {
        // 如果沒有版本信息，使用當前文件內容作為原始內容
        const previewResponse = await previewFile(fileId);
        if (previewResponse.success && previewResponse.data?.content) {
          setOriginalContent(previewResponse.data.content);
        } else {
          setOriginalContent('');
        }
        return;
      }

      // 獲取當前版本（最新的穩定版本）
      const currentVersion = versionsResponse.data.doc_version || 1;
      const versions = versionsResponse.data.versions || [];
      
      // 如果沒有版本信息，使用當前文件內容作為原始內容
      // 否則使用最新版本的內容
      if (versions.length === 0 || currentVersion === 1) {
        // 獲取當前文件內容作為原始內容
        const previewResponse = await previewFile(fileId);
        
        if (previewResponse.success && previewResponse.data?.content) {
          setOriginalContent(previewResponse.data.content);
        } else {
          // 如果無法獲取，使用空字符串
          setOriginalContent('');
        }
      } else {
        // 獲取最新版本的內容
        const latestVersion = versions[versions.length - 1];
        if (latestVersion.version_file_id) {
          // 通過版本文件 ID 獲取內容
          const versionContentResponse = await previewFile(latestVersion.version_file_id);
          
          if (versionContentResponse.success && versionContentResponse.data?.content) {
            setOriginalContent(versionContentResponse.data.content);
          } else {
            setOriginalContent('');
          }
        } else {
          setOriginalContent('');
        }
      }
    } catch (error) {
      console.error('Failed to load original version:', error);
      toast.error('載入原始版本失敗');
      setOriginalContent('');
    } finally {
      setIsLoading(false);
    }
  }, [fileId]);

  // 當 Modal 打開時載入原始版本
  useEffect(() => {
    if (isOpen) {
      loadOriginalVersion();
      setCurrentChangeIndex(0);
      setTotalChanges(0);
    }
  }, [isOpen, loadOriginalVersion]);

  // 更新變更統計
  useEffect(() => {
    if (diffEditor) {
      const changes = diffEditor.getLineChanges();
      if (changes) {
        setTotalChanges(changes.length);
        if (changes.length > 0 && currentChangeIndex >= changes.length) {
          setCurrentChangeIndex(0);
        }
      }
    }
  }, [diffEditor, originalContent, modifiedContent, currentChangeIndex]);

  const handleEditorMount = (editor: editor.IStandaloneDiffEditor) => {
    setDiffEditor(editor);
    
    // 初始化變更統計
    const changes = editor.getLineChanges();
    if (changes) {
      setTotalChanges(changes.length);
      setCurrentChangeIndex(0);
    }
  };

  const handleClose = () => {
    setDiffEditor(null);
    setCurrentChangeIndex(0);
    setTotalChanges(0);
    onClose();
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="relative w-full h-full max-w-7xl max-h-[90vh] m-4 bg-white dark:bg-gray-900 rounded-lg shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            審查變更
          </h2>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            title="關閉"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Change Navigation */}
        <ChangeNavigation
          diffEditor={diffEditor}
          currentIndex={currentChangeIndex}
          totalChanges={totalChanges}
          onIndexChange={setCurrentChangeIndex}
        />

        {/* Diff Editor */}
        <div className="flex-1 min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-gray-500 dark:text-gray-400">載入中...</div>
            </div>
          ) : (
            <MonacoDiffEditor
              original={originalContent}
              modified={modifiedContent}
              language="markdown"
              theme="vs-dark"
              onMount={handleEditorMount}
              height="100%"
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
          >
            取消
          </button>
          <button
            onClick={() => {
              if (onCommit) {
                onCommit();
              }
              handleClose();
            }}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md transition-colors"
          >
            提交變更
          </button>
        </div>
      </div>
    </div>
  );
}

