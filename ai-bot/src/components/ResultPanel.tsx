import { useState, useEffect, useRef } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import FileTree, { FileNode } from './FileTree';
import FileViewer from './FileViewer';
import FileSearchModal from './FileSearchModal';
import FileUploadModal, { FileWithMetadata } from './FileUploadModal';
import FileLibraryModal from './FileLibraryModal';
import UploadProgress from './UploadProgress';
import { useKeyboardShortcuts } from '../lib/hooks/useKeyboardShortcuts';
import { getMockFileContent, getMockFile, getMockFiles } from '../lib/mockFileStorage';
import { getFileTree, FileTreeResponse, previewFile, uploadFiles, uploadFromLibrary, returnToLibrary, syncFiles, searchLibrary } from '../lib/api';

interface ResultPanelProps {
  collapsed: boolean;
  wasCollapsed?: boolean;
  onToggle: () => void;
  onViewChange?: (isMarkdownView: boolean) => void;
  fileTree?: FileNode[]; // 文件樹數據
  onFileTreeChange?: (fileTree: FileNode[]) => void; // 文件樹變化回調
  taskId?: string | number; // 任務 ID，如果沒有則不顯示文件樹
  userId?: string; // 用戶 ID
}

export default function ResultPanel({ collapsed, wasCollapsed, onToggle, onViewChange, fileTree, onFileTreeChange, taskId, userId }: ResultPanelProps) {
  const [activeTab, setActiveTab] = useState<'files' | 'preview'>('files');

  useEffect(() => {
    console.log('[ResultPanel] Component mounted/updated', { taskId, userId, activeTab, hasFileTree: !!fileTree });
  }, [taskId, userId, activeTab, fileTree]);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string | null>(null);
  const [showMoreMenu, setShowMoreMenu] = useState(false);
  const [fileTreeData, setFileTreeData] = useState<FileTreeResponse | null>(null);
  const [fileContent, setFileContent] = useState<string | undefined>(undefined);
  const [isLoadingContent, setIsLoadingContent] = useState(false);
  const [showSearchModal, setShowSearchModal] = useState(false);
  const [focusedFolderId, setFocusedFolderId] = useState<string | null>(null); // 當前聚焦的資料夾ID
  const [triggerNewFolder, setTriggerNewFolder] = useState(false); // 觸發新增資料夾的標誌
  const [showFileUploadModal, setShowFileUploadModal] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<FileWithMetadata[]>([]);
  const [showFileLibraryModal, setShowFileLibraryModal] = useState(false);
  const [libraryAction, setLibraryAction] = useState<'upload' | 'return' | null>(null);
  const [syncResult, setSyncResult] = useState<any>(null);
  const moreMenuRef = useRef<HTMLDivElement>(null);
  const { t } = useLanguage();

  // 從後端 API 獲取文件樹數據（用於查找文件名）
  useEffect(() => {
    if (taskId && userId) {
      getFileTree({ user_id: userId, task_id: String(taskId) })
        .then((response) => {
          if (response.success && response.data) {
            setFileTreeData(response);
          }
        })
        .catch(() => {
          // 忽略錯誤，使用其他方式查找文件名
        });
    }
  }, [taskId, userId]);

  // 當面板從收攏狀態變為展開狀態時，重置為文件目錄模式
  useEffect(() => {
    // 如果之前是收攏狀態（wasCollapsed === true），現在是展開狀態（collapsed === false），則重置
      if (wasCollapsed === true && !collapsed) {
      setActiveTab('files');
      setSelectedFile(null);
      setSelectedFileName(null);
      if (onViewChange) {
        onViewChange(false);
      }
    }
  }, [collapsed, wasCollapsed, onViewChange]);

  // 點擊外部關閉更多菜單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (moreMenuRef.current && !moreMenuRef.current.contains(event.target as Node)) {
        setShowMoreMenu(false);
      }
    };

    if (showMoreMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMoreMenu]);

  // 模擬文件 URL（實際應該從 API 獲取）
  const getFileUrl = (fileNameOrId: string): string => {
    // 如果是模擬文件，返回特殊的 URL
    if (taskId) {
      // 嘗試從模擬存儲中查找文件（先嘗試作為 fileId，再嘗試作為 fileName）
      const mockFile = getMockFile(String(taskId), fileNameOrId);
      if (!mockFile) {
        // 如果沒找到，嘗試通過文件名查找
        const mockFiles = getMockFiles(String(taskId));
        const foundFile = mockFiles.find((f: any) => f.filename === fileNameOrId);
        if (foundFile) {
          return `/api/mock-files/${taskId}/${encodeURIComponent(foundFile.file_id)}`;
        }
      } else {
        // 返回模擬文件的 URL（用於識別）
        return `/api/mock-files/${taskId}/${encodeURIComponent(mockFile.file_id)}`;
      }
    }
    // 這裡應該根據實際情況構建文件 URL
    // 暫時使用模擬 URL
    return `/api/files/${encodeURIComponent(fileNameOrId)}`;
  };

  // 獲取文件內容（從模擬存儲或後端 API）
  useEffect(() => {
    if (!selectedFile) {
      setFileContent(undefined);
      return;
    }

    setIsLoadingContent(true);

    // 優先從模擬存儲中獲取文件內容
    if (taskId) {
      // 先嘗試作為 fileId 查找
      let mockFile = getMockFile(String(taskId), selectedFile);
      if (!mockFile) {
        // 如果沒找到，嘗試通過文件名查找
        const mockFiles = getMockFiles(String(taskId));
        mockFile = mockFiles.find((f: any) => f.filename === selectedFile);
      }

      if (mockFile) {
        // 如果是 Markdown 文件且有內容，使用模擬內容
        const content = getMockFileContent(String(taskId), mockFile.file_id);
        if (content) {
          setFileContent(content);
          setIsLoadingContent(false);
          return;
        }
      }
    }

    // 如果沒有模擬文件，嘗試從後端 API 獲取
    previewFile(selectedFile)
      .then((response) => {
        if (response.success && response.data) {
          setFileContent(response.data.content);
        } else {
          // 如果 API 調用失敗，使用默認內容
          const extension = selectedFile.split('.').pop()?.toLowerCase();
          if (extension === 'md' || extension === 'markdown') {
            setFileContent(`# ${selectedFile}\n\n## 概述\n\n無法加載文件內容。`);
          } else {
            setFileContent(undefined);
          }
        }
        setIsLoadingContent(false);
      })
      .catch((error) => {
        // API 調用失敗，使用默認內容
        console.warn('Failed to preview file from API:', error);
        const extension = selectedFile.split('.').pop()?.toLowerCase();
        if (extension === 'md' || extension === 'markdown') {
          setFileContent(`# ${selectedFile}\n\n## 概述\n\n無法加載文件內容。`);
        } else {
          setFileContent(undefined);
        }
        setIsLoadingContent(false);
      });
  }, [selectedFile, taskId]);

  const handleFileSelect = (fileId: string, fileName?: string) => {
    // 保存 fileId 和 fileName，用於後續查找文件內容
    setSelectedFile(fileId);
    // 保存 fileName，用於文件預覽時顯示正確的文件名
    setSelectedFileName(fileName || null);
    setActiveTab('preview');
    if (onViewChange) {
      onViewChange(true);
    }
  };

  const handleNewFolder = () => {
    // 觸發 FileTree 組件的新增資料夾功能
    // FileTree 會根據 focus 狀態決定新增位置：
    // - 如果 focus 在資料夾上，在該資料夾下新增（parent_task_id = focusedFolderId）
    // - 如果沒有 focus，在與「任務工作區」同級目錄新增（parent_task_id = null）
    setTriggerNewFolder(true);
  };

  const handleNewFolderTriggered = () => {
    // 重置觸發標誌
    setTriggerNewFolder(false);
  };

  const handleNewFile = () => {
    // 根據 focus 狀態決定新增位置
    // 如果 focus 在資料夾上，在該資料夾下新增檔案
    // 如果沒有 focus，在「任務工作區」新增檔案
    setShowFileUploadModal(true);
  };

  const handleFileUpload = async (files: File[], uploadTaskId?: string) => {
    if (files.length === 0) return;

    // 確定目標任務ID：優先使用傳遞的 taskId，否則使用聚焦的資料夾ID，最後使用當前任務ID或任務工作區
    const targetTaskId = uploadTaskId || focusedFolderId || (taskId ? String(taskId) : 'temp-workspace');

    // 創建文件元數據
    const filesWithMetadata: FileWithMetadata[] = files.map((file) => ({
      file,
      id: `${Date.now()}-${Math.random()}`,
      status: 'pending',
      progress: 0,
    }));

    setUploadingFiles(filesWithMetadata);

    try {
      // 更新所有文件狀態為上傳中
      setUploadingFiles((prev) =>
        prev.map((f) => ({ ...f, status: 'uploading' }))
      );

      const response = await uploadFiles(files, (progress) => {
        // 更新總體進度到所有文件
        setUploadingFiles((prev) =>
          prev.map((f) => ({ ...f, progress }))
        );
      }, targetTaskId);

      // 處理上傳結果
      if (response.success && response.data) {
        const uploadedMap = new Map(
          response.data.uploaded?.map((u: any) => [u.filename, u]) || []
        );
        const errorsMap = new Map(
          response.data.errors?.map((e: any) => [e.filename, e.error]) || []
        );

        // 更新每個文件的狀態
        setUploadingFiles((prev) =>
          prev.map((f) => {
            if (uploadedMap.has(f.file.name)) {
              return { ...f, status: 'success', progress: 100 };
            } else if (errorsMap.has(f.file.name)) {
              return {
                ...f,
                status: 'error',
                error: errorsMap.get(f.file.name) || '上傳失敗',
              };
            } else {
              return {
                ...f,
                status: 'error',
                error: '未知錯誤',
              };
            }
          })
        );

        // 觸發文件上傳完成事件，通知文件管理頁面刷新
        window.dispatchEvent(new CustomEvent('fileUploaded', {
          detail: { fileIds: response.data.uploaded?.map((u: any) => u.file_id) || [] }
        }));

        // 觸發文件樹更新事件，通知父組件更新文件樹
        if (response.data.uploaded && response.data.uploaded.length > 0) {
          window.dispatchEvent(new CustomEvent('filesUploaded', {
            detail: {
              taskId: targetTaskId,
              files: response.data.uploaded.map((u: any) => ({
                file_id: u.file_id,
                filename: u.filename,
                file_type: u.file_type,
                file_size: u.file_size,
              }))
            }
          }));
        }

        // 所有文件處理完成後，等待3秒後清除
        setTimeout(() => {
          setUploadingFiles([]);
        }, 3000);
      } else {
        // 整體失敗
        setUploadingFiles((prev) =>
          prev.map((f) => ({
            ...f,
            status: 'error',
            error: response.message || response.error || '上傳失敗',
          }))
        );
      }
    } catch (error: any) {
      console.error('File upload error:', error);

      // 如果後端不可用，嘗試使用模擬文件上傳
      if (error.message?.includes('網絡錯誤') || error.message?.includes('ERR_CONNECTION_TIMED_OUT') || error.message?.includes('Failed to fetch')) {
        try {
          const { uploadMockFiles } = await import('../lib/mockFileStorage');
          const userId = localStorage.getItem('userEmail') || undefined;
          const result = await uploadMockFiles(files, targetTaskId, userId);

          // 更新文件狀態
          setUploadingFiles((prev) =>
            prev.map((f) => {
              const uploaded = result.uploaded.find((u) => u.filename === f.file.name);
              const error = result.errors.find((e) => e.filename === f.file.name);

              if (uploaded) {
                return { ...f, status: 'success', progress: 100 };
              } else if (error) {
                return { ...f, status: 'error', error: error.error };
              } else {
                return { ...f, status: 'error', error: '上傳失敗' };
              }
            })
          );

          // 觸發文件上傳完成事件
          window.dispatchEvent(new CustomEvent('fileUploaded', {
            detail: { fileIds: result.uploaded.map((u) => u.file_id) }
          }));

          // 觸發文件樹更新事件
          window.dispatchEvent(new CustomEvent('mockFilesUploaded', {
            detail: { taskId: targetTaskId, files: result.uploaded }
          }));

          // 所有文件處理完成後，等待3秒後清除
          setTimeout(() => {
            setUploadingFiles([]);
          }, 3000);

          return;
        } catch (mockError: any) {
          console.error('Mock file upload error:', mockError);
        }
      }

      // 處理錯誤
      setUploadingFiles((prev) =>
        prev.map((f) => ({
          ...f,
          status: 'error',
          error: error.message || '上傳失敗',
        }))
      );
    }
  };

  const handleCancelUpload = (fileId: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleDismissUpload = (fileId: string) => {
    setUploadingFiles((prev) => prev.filter((f) => f.id !== fileId));
  };

  const handleSearch = () => {
    setShowSearchModal(true);
  };

  // 全局快捷鍵
  useKeyboardShortcuts({
    onSearch: () => {
      // Cmd/Ctrl + P: 打開搜尋檔案對話框
      if (!showSearchModal && !showFileUploadModal && !showFileLibraryModal) {
        setShowSearchModal(true);
      }
    },
    onEscape: () => {
      // Esc: 關閉當前對話框
      if (showSearchModal) {
        setShowSearchModal(false);
      }
      if (showFileUploadModal) {
        setShowFileUploadModal(false);
      }
      if (showFileLibraryModal) {
        setShowFileLibraryModal(false);
      }
      if (showMoreMenu) {
        setShowMoreMenu(false);
      }
    },
    enabled: true,
  });

  // Cmd/Ctrl + F: 在當前視圖中搜尋
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 檢查是否在輸入框中（不響應快捷鍵）
      const target = e.target as HTMLElement;
      const isInputFocused =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Cmd/Ctrl + F: 在當前視圖中搜尋（與全局搜尋 Cmd/Ctrl + P 區分）
      if ((e.metaKey || e.ctrlKey) && e.key === 'f' && !isInputFocused) {
        // 如果當前在文件目錄模式，打開搜尋對話框
        if (activeTab === 'files') {
          e.preventDefault();
          setShowSearchModal(true);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [activeTab, showSearchModal]);

  const handleUploadFromLibrary = () => {
    setLibraryAction('upload');
    setShowFileLibraryModal(true);
    setShowMoreMenu(false);
  };

  const handleSendToLibrary = async () => {
    // 獲取當前任務的所有文件ID（簡化實現，實際應該從文件樹獲取選中的文件）
    if (!taskId) {
      alert('請先選擇一個任務');
      setShowMoreMenu(false);
      return;
    }

    // 確認對話框
    if (!confirm('確定要將當前任務的所有文件傳回文件庫嗎？')) {
      setShowMoreMenu(false);
      return;
    }

    try {
      // 獲取當前任務的文件列表
      const fileTreeResponse = await getFileTree({
        user_id: userId,
        task_id: String(taskId),
      });

      if (fileTreeResponse.success && fileTreeResponse.data?.tree) {
        const taskFiles = fileTreeResponse.data.tree[String(taskId)] || [];
        const fileIds = taskFiles.map((f: any) => f.file_id);

        if (fileIds.length === 0) {
          alert('當前任務沒有文件');
          setShowMoreMenu(false);
          return;
        }

        const response = await returnToLibrary(fileIds);
        if (response.success) {
          alert(`成功傳回 ${response.data?.returned_count || 0} 個文件到文件庫`);
          // 觸發文件樹更新
          window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
        } else {
          alert(`傳回文件庫失敗: ${response.message || '未知錯誤'}`);
        }
      }
    } catch (error: any) {
      console.error('傳回文件庫失敗:', error);
      alert(`傳回文件庫失敗: ${error.message || '未知錯誤'}`);
    }

    setShowMoreMenu(false);
  };

  const handleSyncFiles = async () => {
    if (!taskId) {
      alert('請先選擇一個任務');
      setShowMoreMenu(false);
      return;
    }

    try {
      const response = await syncFiles({ task_id: String(taskId) });
      if (response.success && response.data) {
        setSyncResult(response.data);
        alert(`同步完成：${response.data.synced.length} 個文件已同步`);
        // 觸發文件樹更新
        window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
      } else {
        alert(`同步失敗: ${response.message || '未知錯誤'}`);
      }
    } catch (error: any) {
      console.error('同步文件失敗:', error);
      alert(`同步文件失敗: ${error.message || '未知錯誤'}`);
    }

    setShowMoreMenu(false);
  };

  const handleSearchLibrary = () => {
    setLibraryAction('upload'); // 搜尋後可以選擇上傳
    setShowFileLibraryModal(true);
    setShowMoreMenu(false);
  };

  const handleLibraryFileSelect = async (fileIds: string[]) => {
    if (libraryAction === 'upload') {
      const targetTaskId = focusedFolderId || (taskId ? String(taskId) : 'temp-workspace');

      try {
        const response = await uploadFromLibrary(fileIds, targetTaskId);
        if (response.success) {
          alert(`成功上傳 ${response.data?.uploaded_count || 0} 個文件`);
          // 觸發文件樹更新
          window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
        } else {
          alert(`上傳失敗: ${response.message || '未知錯誤'}`);
        }
      } catch (error: any) {
        console.error('從文件庫上傳失敗:', error);
        alert(`從文件庫上傳失敗: ${error.message || '未知錯誤'}`);
      }
    }

    setShowFileLibraryModal(false);
    setLibraryAction(null);
  };

  return (
    <div className={cn(
      "h-full bg-secondary border-l border-primary flex flex-col transition-all duration-300 w-full theme-transition"
    )}>
      {/* 结果面板头部 */}
      <div className="p-4 border-b border-primary flex items-center">
        <div className="flex space-x-2">
          <button
            className={`px-3 py-1 rounded-t-lg text-sm ${activeTab === 'files' ? 'bg-tertiary text-primary' : 'text-tertiary'}`}
            onClick={() => {
              setActiveTab('files');
              if (onViewChange) {
                onViewChange(false);
              }
            }}
          >
            {t('resultPanel.files')}
          </button>
          <button
            className={`px-3 py-1 rounded-t-lg text-sm ${activeTab === 'preview' ? 'bg-tertiary text-primary' : 'text-tertiary'}`}
            onClick={() => {
              if (selectedFile) {
                setActiveTab('preview');
                if (onViewChange) {
                  onViewChange(true);
                }
              }
            }}
            disabled={!selectedFile}
          >
            {t('resultPanel.preview')}
          </button>
        </div>
      </div>

      {/* 工具列 - 只在文件目錄模式顯示，位於 header 下方 */}
      {activeTab === 'files' && (
        <div className="px-4 py-2 border-b border-primary flex items-center space-x-2 bg-secondary theme-transition">
          <button
            onClick={handleNewFolder}
            className="flex items-center justify-center w-8 h-8 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
            title={t('resultPanel.newFolder', '新增目錄')}
            aria-label={t('resultPanel.newFolder', '新增目錄')}
          >
            <i className="fa-solid fa-folder-plus"></i>
          </button>
          <button
            onClick={handleNewFile}
            className="flex items-center justify-center w-8 h-8 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
            title={t('resultPanel.newFile', '新增檔案')}
            aria-label={t('resultPanel.newFile', '新增檔案')}
          >
            <span className="relative">
              <i className="fa-solid fa-file"></i>
              <i className="fa-solid fa-plus absolute -top-1 -right-1 text-xs bg-primary rounded-full w-3 h-3 flex items-center justify-center" style={{ fontSize: '0.5rem' }}></i>
            </span>
          </button>
          {/* 分隔線 */}
          <div className="h-6 w-px bg-primary mx-1"></div>
          {/* 搜尋按鈕 */}
          <button
            onClick={handleSearch}
            className="flex items-center justify-center w-8 h-8 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
            title={t('resultPanel.search', '搜尋文件')}
            aria-label={t('resultPanel.search', '搜尋文件')}
          >
            <i className="fa-solid fa-magnifying-glass"></i>
          </button>
          {/* 分隔線 */}
          <div className="h-6 w-px bg-primary mx-1"></div>
          {/* 更多選單 */}
          <div className="relative ml-auto" ref={moreMenuRef}>
            <button
              onClick={() => setShowMoreMenu(!showMoreMenu)}
              className="flex items-center justify-center w-8 h-8 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
              title={t('resultPanel.more', '更多選項')}
              aria-label={t('resultPanel.more', '更多選項')}
            >
              <i className="fa-solid fa-ellipsis"></i>
            </button>
            {/* 下拉菜單 */}
            {showMoreMenu && (
              <div className="absolute right-0 top-full mt-1 w-48 bg-secondary border border-primary rounded-lg shadow-lg z-50 theme-transition overflow-hidden">
                <button
                  onClick={handleUploadFromLibrary}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary hover:text-primary transition-all duration-200 flex items-center text-primary group"
                >
                  <i className="fa-solid fa-upload mr-2 text-tertiary group-hover:text-blue-400 transition-colors duration-200"></i>
                  {t('resultPanel.uploadFromLibrary', '從文件庫上傳')}
                </button>
                <button
                  onClick={handleSendToLibrary}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary hover:text-primary transition-all duration-200 flex items-center text-primary group"
                >
                  <i className="fa-solid fa-download mr-2 text-tertiary group-hover:text-green-400 transition-colors duration-200"></i>
                  {t('resultPanel.sendToLibrary', '傳回文件庫')}
                </button>
                <button
                  onClick={handleSyncFiles}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary hover:text-primary transition-all duration-200 flex items-center text-primary group"
                >
                  <i className="fa-solid fa-arrows-rotate mr-2 text-tertiary group-hover:text-purple-400 transition-colors duration-200"></i>
                  {t('resultPanel.syncFiles', '同步文件')}
                </button>
                <button
                  onClick={handleSearchLibrary}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary hover:text-primary transition-all duration-200 flex items-center text-primary group"
                >
                  <i className="fa-solid fa-magnifying-glass mr-2 text-tertiary group-hover:text-orange-400 transition-colors duration-200"></i>
                  {t('resultPanel.searchLibrary', '搜尋文件庫')}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 结果面板内容 */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'files' && (() => {
          console.log('[ResultPanel] Rendering FileTree', { taskId, userId, hasFileTree: !!fileTree, fileTreeLength: fileTree?.length });
          return (
            <FileTree
              taskId={taskId ? String(taskId) : undefined}
              userId={userId}
              onFileSelect={handleFileSelect}
              fileTree={fileTree}
              onFileTreeChange={onFileTreeChange}
              onFolderFocus={setFocusedFolderId}
              onNewFile={(targetTaskId) => {
                // 設置聚焦狀態並打開上傳對話框
                setFocusedFolderId(targetTaskId);
                setShowFileUploadModal(true);
              }}
              triggerNewFolder={triggerNewFolder}
              onNewFolderTriggered={handleNewFolderTriggered}
            />
          );
        })()}
        {activeTab === 'preview' && selectedFile && (() => {
          // 優先使用保存的文件名，如果沒有則嘗試從多個來源查找
          let displayFileName = selectedFileName || selectedFile;

          // 如果沒有保存的文件名，嘗試從多個來源查找
          if (!selectedFileName) {
            // 1. 嘗試從模擬存儲中獲取文件名
            if (taskId) {
              const mockFile = getMockFile(String(taskId), selectedFile);
              if (mockFile) {
                displayFileName = mockFile.filename;
              }
            }

            // 2. 如果還沒找到，嘗試從 fileTree prop 中查找
            if (displayFileName === selectedFile && fileTree) {
              const fileNode = fileTree.find((node) => node.id === selectedFile);
              if (fileNode) {
                displayFileName = fileNode.name;
              }
            }

            // 3. 如果還是沒找到，嘗試從後端 API 返回的文件樹數據中查找
            if (displayFileName === selectedFile && fileTreeData?.data?.tree) {
              for (const taskFiles of Object.values(fileTreeData.data.tree)) {
                const file = taskFiles.find((f) => f.file_id === selectedFile);
                if (file && file.filename) {
                  displayFileName = file.filename;
                  break;
                }
              }
            }
          }

          // 確保 displayFileName 有擴展名，否則 FileViewer 無法識別文件類型
          // 如果 displayFileName 仍然是 fileId（沒有擴展名），嘗試從後端獲取文件元數據
          // 這裡暫時使用 fileId，但應該調用 API 獲取文件元數據

          // 如果正在加載內容，顯示加載提示
          if (isLoadingContent) {
            return (
              <div className="p-4 h-full flex items-center justify-center text-tertiary">
                <div className="text-center">
                  <i className="fa-solid fa-spinner fa-spin text-4xl mb-4"></i>
                  <p>正在加載文件內容...</p>
                </div>
              </div>
            );
          }

          return (
          <FileViewer
            fileUrl={getFileUrl(selectedFile)}
            fileName={displayFileName}
            content={fileContent}
          />
          );
        })()}
        {activeTab === 'preview' && !selectedFile && (
          <div className="p-4 h-full flex items-center justify-center text-tertiary">
            {t('resultPanel.noFileSelected', '請選擇一個文件進行預覽')}
          </div>
        )}
      </div>

      {/* 搜尋對話框 */}
      <FileSearchModal
        isOpen={showSearchModal}
        onClose={() => setShowSearchModal(false)}
        onFileSelect={handleFileSelect}
        taskId={taskId ? String(taskId) : undefined}
        userId={userId}
        fileTree={fileTree}
      />

      {/* 文件上傳對話框 */}
      <FileUploadModal
        isOpen={showFileUploadModal}
        onClose={() => setShowFileUploadModal(false)}
        onUpload={handleFileUpload}
        defaultTaskId={focusedFolderId || (taskId ? String(taskId) : 'temp-workspace')}
      />

      {/* 文件庫選擇對話框 */}
      <FileLibraryModal
        isOpen={showFileLibraryModal}
        onClose={() => {
          setShowFileLibraryModal(false);
          setLibraryAction(null);
        }}
        onSelect={handleLibraryFileSelect}
        userId={userId}
      />

      {/* 上傳進度顯示 */}
      {uploadingFiles.length > 0 && (
        <UploadProgress
          files={uploadingFiles}
          onCancel={handleCancelUpload}
          onDismiss={handleDismissUpload}
        />
      )}
    </div>
  );
}
