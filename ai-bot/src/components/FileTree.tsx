/**
 * 代碼功能說明: 文件樹組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 *
 * 功能說明:
 * - 顯示按 task_id 組織的文件目錄結構
 * - 支持展開/折疊目錄
 * - 點擊目錄可以篩選文件列表
 * - 顯示"任務工作區"作為特殊目錄
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Folder, FolderOpen, File as FileIcon, ChevronRight, ChevronDown, X } from 'lucide-react';
import { getFileTree, FileTreeResponse, getFileList, deleteFile, renameFile, copyFile, moveFile, renameFolder, createFolder, deleteFolder } from '../lib/api';
import { FileNode } from './Sidebar';
import { getMockFiles, hasMockFiles, getMockFile } from '../lib/mockFileStorage';
import { useClipboardState, useBatchSelection, saveClipboardState, loadClipboardState, ClipboardItem } from '../lib/fileOperationState';

// 導出 FileNode 類型供其他組件使用
export type { FileNode };

interface FileTreeProps {
  userId?: string;
  taskId?: string; // 任務 ID，如果沒有則不顯示文件樹
  onTaskSelect?: (taskId: string | null) => void;
  selectedTaskId?: string | null;
  fileTree?: FileNode[]; // 可選：直接傳入文件樹數據
  onFileTreeChange?: (fileTree: FileNode[]) => void; // 文件樹變化回調
  onFileSelect?: (fileId: string, fileName?: string) => void; // 文件選擇回調，可選傳遞文件名
  onFolderFocus?: (folderId: string | null) => void; // 資料夾聚焦回調
  onNewFile?: (taskId: string) => void; // 新增檔案回調，傳遞目標任務ID
  triggerNewFolder?: boolean; // 外部觸發新增資料夾的標誌
  onNewFolderTriggered?: () => void; // 新增資料夾觸發後的回調
}

interface TreeNode {
  taskId: string;
  taskName: string;
  fileCount: number;
  isExpanded: boolean;
}

const TEMP_WORKSPACE_ID = 'temp-workspace';
const TEMP_WORKSPACE_NAME = '任務工作區';

export default function FileTree({
  userId,
  taskId,
  onTaskSelect,
  selectedTaskId,
  fileTree,
  onFileTreeChange,
  onFileSelect,
  onFolderFocus,
  onNewFile,
  triggerNewFolder,
  onNewFolderTriggered
}: FileTreeProps) {
  const [treeData, setTreeData] = useState<FileTreeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set([TEMP_WORKSPACE_ID])); // 默認展開任務工作區
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; fileId: string; fileName: string } | null>(null);
  const [folderContextMenu, setFolderContextMenu] = useState<{ x: number; y: number; taskId: string; taskName: string } | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null); // 選中的文件ID
  const [showFileInfoModal, setShowFileInfoModal] = useState(false);
  const [fileInfo, setFileInfo] = useState<{ fileId: string; fileName: string } | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [keyboardSelectedIndex, setKeyboardSelectedIndex] = useState<number>(-1); // 鍵盤導航選中的索引
  const [keyboardSelectedType, setKeyboardSelectedType] = useState<'file' | 'folder' | null>(null); // 鍵盤選中的類型
  const [focusedFolderId, setFocusedFolderId] = useState<string | null>(null); // 當前聚焦的資料夾ID
  const [showRenameModal, setShowRenameModal] = useState(false); // 顯示重命名對話框
  const [renameTarget, setRenameTarget] = useState<{ id: string; name: string; type: 'folder' | 'file' } | null>(null); // 重命名目標
  const [renameInput, setRenameInput] = useState(''); // 重命名輸入值
  const [showNewFolderModal, setShowNewFolderModal] = useState(false); // 顯示新增資料夾對話框
  const [newFolderParentId, setNewFolderParentId] = useState<string | null>(null); // 新增資料夾的父資料夾ID
  const [newFolderInput, setNewFolderInput] = useState(''); // 新增資料夾輸入值
  const [showDeleteFolderModal, setShowDeleteFolderModal] = useState(false); // 顯示刪除資料夾確認對話框
  const [deleteFolderTarget, setDeleteFolderTarget] = useState<{ taskId: string; taskName: string } | null>(null); // 要刪除的資料夾
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const folderContextMenuRef = useRef<HTMLDivElement>(null);
  const fileTreeRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const newFolderInputRef = useRef<HTMLInputElement>(null);
  const folderRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // 使用剪貼板和批量選擇功能
  const { setClipboard } = useClipboardState();
  const batchSelection = useBatchSelection();

  // 處理重命名確認
  const handleRenameConfirm = useCallback(() => {
    if (!renameTarget || !renameInput.trim() || renameInput.trim() === renameTarget.name) {
      return;
    }


    // 檢查是否為 temp-workspace（只有資料夾需要檢查，文件不需要）
    // 文件重命名時，renameTarget.id 是 file_id，不會是 temp-workspace
    if (renameTarget.type === 'folder') {
      // 只有當類型明確為 'folder' 且 ID 為 temp-workspace 時才顯示錯誤
      if (renameTarget.id === TEMP_WORKSPACE_ID) {
        console.warn('[FileTree] Attempted to rename temp-workspace folder', {
          type: renameTarget.type,
          id: renameTarget.id,
          name: renameTarget.name
        });
        setNotification({ message: '任務工作區無法重命名', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
        setShowRenameModal(false);
        setRenameTarget(null);
        setRenameInput('');
        return;
      }

      // 資料夾重命名
      renameFolder(renameTarget.id, renameInput.trim())
        .then((result) => {
          if (result.success) {
            setNotification({ message: '資料夾重命名成功', type: 'success' });
            setTimeout(() => setNotification(null), 3000);
            // 觸發文件樹更新
            window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
          } else {
            setNotification({ message: result.message || '資料夾重命名失敗', type: 'error' });
            setTimeout(() => setNotification(null), 3000);
          }
        })
        .catch((error) => {
          console.error('資料夾重命名失敗:', error);
          setNotification({ message: error.message || '資料夾重命名失敗', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
        });
    } else if (renameTarget.type === 'file') {
      // 文件重命名：絕對不會檢查 temp-workspace，因為文件 ID 不可能是 temp-workspace
      renameFile(renameTarget.id, renameInput.trim())
        .then((result) => {
          if (result.success) {
            setNotification({ message: '文件重命名成功', type: 'success' });
            setTimeout(() => setNotification(null), 3000);
            // 觸發文件樹更新
            window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
          } else {
            setNotification({ message: result.message || '文件重命名失敗', type: 'error' });
            setTimeout(() => setNotification(null), 3000);
          }
        })
        .catch((error) => {
          console.error('文件重命名失敗:', error);
          setNotification({ message: error.message || '文件重命名失敗', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
        });
    } else {
      console.error('[FileTree] Unknown rename target type:', renameTarget.type);
      setNotification({ message: '未知的重命名類型', type: 'error' });
      setTimeout(() => setNotification(null), 3000);
    }

    setShowRenameModal(false);
    setRenameTarget(null);
    setRenameInput('');
  }, [renameTarget, renameInput]);

  // 處理重命名取消
  const handleRenameCancel = useCallback(() => {
    setShowRenameModal(false);
    setRenameTarget(null);
    setRenameInput('');
  }, []);

  // 當重命名對話框打開時，聚焦輸入框
  useEffect(() => {
    if (showRenameModal && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [showRenameModal]);

  // 當新增資料夾對話框打開時，聚焦輸入框
  useEffect(() => {
    if (showNewFolderModal && newFolderInputRef.current) {
      newFolderInputRef.current.focus();
    }
  }, [showNewFolderModal]);

  // 監聽外部觸發新增資料夾
  useEffect(() => {
    if (triggerNewFolder) {
      // 根據 focus 狀態決定新增位置
      // 1. 如果 focus 在資料夾上（包括「任務工作區」），在該資料夾下新增（parent_task_id = focusedFolderId）
      // 2. 如果沒有 focus（focusedFolderId 為 null），在根節點新增（parent_task_id = null，與任務工作區同級）
      const parentId = focusedFolderId; // 如果 focusedFolderId 為 null，則 parentId 也是 null
      setNewFolderParentId(parentId);
      setNewFolderInput('');
      setShowNewFolderModal(true);

      // 通知父組件已處理觸發
      if (onNewFolderTriggered) {
        onNewFolderTriggered();
      }
    }
  }, [triggerNewFolder, focusedFolderId, onNewFolderTriggered]);

  // 處理新增資料夾確認
  const handleNewFolderConfirm = useCallback(() => {
    if (!newFolderInput.trim()) {
      return;
    }

      folderName: newFolderInput.trim(),
      parentTaskId: newFolderParentId,
      isRootLevel: newFolderParentId === null
    });

    // 如果 newFolderParentId 是 null，传递 null 给后端（在根节点创建）
    // 如果 newFolderParentId 是 undefined，传递 undefined（使用默认值）
    // 如果 newFolderParentId 有值，传递该值（在指定文件夹下创建）
    const parentIdToSend = newFolderParentId === null ? null : (newFolderParentId || undefined);
    createFolder(newFolderInput.trim(), parentIdToSend)
      .then((result) => {
        if (result.success) {
          setNotification({ message: '資料夾創建成功', type: 'success' });
          setTimeout(() => setNotification(null), 3000);
          // 觸發文件樹更新
          window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
        } else {
          setNotification({ message: result.message || '資料夾創建失敗', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
        }
      })
      .catch((error) => {
        console.error('資料夾創建失敗:', error);
        setNotification({ message: error.message || '資料夾創建失敗', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
      });

    setShowNewFolderModal(false);
    setNewFolderParentId(null);
    setNewFolderInput('');
  }, [newFolderParentId, newFolderInput]);

  // 處理新增資料夾取消
  const handleNewFolderCancel = useCallback(() => {
    setShowNewFolderModal(false);
    setNewFolderParentId(null);
    setNewFolderInput('');
  }, []);

  // 處理刪除資料夾確認
  const handleDeleteFolderConfirm = useCallback(async () => {
    if (!deleteFolderTarget) {
      return;
    }


    try {
      const result = await deleteFolder(deleteFolderTarget.taskId);
      if (result.success) {
        setNotification({ message: '資料夾刪除成功', type: 'success' });
        setTimeout(() => setNotification(null), 3000);
        // 觸發文件樹更新
        window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
      } else {
        setNotification({ message: result.message || '資料夾刪除失敗', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (error: any) {
      console.error('資料夾刪除失敗:', error);
      setNotification({ message: error.message || '資料夾刪除失敗', type: 'error' });
      setTimeout(() => setNotification(null), 3000);
    }

    setShowDeleteFolderModal(false);
    setDeleteFolderTarget(null);
  }, [deleteFolderTarget]);

  // 處理刪除資料夾取消
  const handleDeleteFolderCancel = useCallback(() => {
    setShowDeleteFolderModal(false);
    setDeleteFolderTarget(null);
  }, []);

  // 切換文件夾展開/折疊狀態
  const toggleTask = useCallback((taskId: string) => {
    setExpandedTasks((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      return newSet;
    });
  }, []);

  // 鍵盤快捷鍵處理
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 檢查是否在輸入框中（不響應快捷鍵）
      const target = e.target as HTMLElement;
      const isInputFocused =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      if (isInputFocused) return;

      // 如果有右鍵選單打開，不響應快捷鍵
      if (contextMenu || folderContextMenu) return;

      // F2: 重新命名選中的文件或資料夾
      if (e.key === 'F2' && selectedFileId) {
        e.preventDefault();
        // 觸發重新命名（需要實現）
      }

      // Delete: 刪除選中的文件或資料夾（需要確認）
      if (e.key === 'Delete' && selectedFileId) {
        e.preventDefault();
        if (confirm('確定要刪除此文件嗎？')) {
          deleteFile(selectedFileId)
            .then((result) => {
              if (result.success) {
                setNotification({ message: '文件已刪除', type: 'success' });
                setTimeout(() => setNotification(null), 3000);
                // 觸發文件樹更新
                window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
              } else {
                setNotification({ message: result.message || '刪除失敗', type: 'error' });
                setTimeout(() => setNotification(null), 3000);
              }
            })
            .catch((error) => {
              console.error('刪除文件失敗:', error);
              setNotification({ message: '刪除文件失敗', type: 'error' });
              setTimeout(() => setNotification(null), 3000);
            });
        }
      }

      // Cmd/Ctrl + C: 複製選中的文件或資料夾
      if ((e.metaKey || e.ctrlKey) && e.key === 'c' && selectedFileId) {
        e.preventDefault();
        const clipboardItems: ClipboardItem[] = [{
          id: selectedFileId,
          type: 'file',
          name: contextMenu?.fileName || selectedFileId,
        }];
        setClipboard({
          type: 'copy',
          items: clipboardItems,
          timestamp: Date.now(),
        });
        setNotification({ message: '文件已複製', type: 'success' });
        setTimeout(() => setNotification(null), 3000);
      }

      // Cmd/Ctrl + X: 剪下選中的文件或資料夾
      if ((e.metaKey || e.ctrlKey) && e.key === 'x' && selectedFileId) {
        e.preventDefault();
        const clipboardItems: ClipboardItem[] = [{
          id: selectedFileId,
          type: 'file',
          name: contextMenu?.fileName || selectedFileId,
        }];
        setClipboard({
          type: 'cut',
          items: clipboardItems,
          timestamp: Date.now(),
        });
        setNotification({ message: '文件已剪下', type: 'success' });
        setTimeout(() => setNotification(null), 3000);
      }

      // Cmd/Ctrl + V: 貼上已複製或剪下的文件或資料夾
      if ((e.metaKey || e.ctrlKey) && e.key === 'v') {
        e.preventDefault();
        const clipboardState = loadClipboardState();
        if (clipboardState && clipboardState.items.length > 0) {
          const targetTaskId = focusedFolderId || (taskId || 'temp-workspace');
          clipboardState.items.forEach((item) => {
            if (item.type === 'file') {
              if (clipboardState.type === 'copy') {
                // 複製文件
                copyFile(item.id, targetTaskId)
                  .then((result) => {
                    if (result.success) {
                      setNotification({ message: '文件已貼上', type: 'success' });
                      setTimeout(() => setNotification(null), 3000);
                      window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
                    }
                  })
                  .catch((error) => {
                    console.error('貼上文件失敗:', error);
                    setNotification({ message: '貼上文件失敗', type: 'error' });
                    setTimeout(() => setNotification(null), 3000);
                  });
              } else if (clipboardState.type === 'cut') {
                // 移動文件
                moveFile(item.id, targetTaskId)
                  .then((result) => {
                    if (result.success) {
                      setNotification({ message: '文件已移動', type: 'success' });
                      setTimeout(() => setNotification(null), 3000);
                      // 清除剪貼板
                      saveClipboardState({ type: 'copy', items: [], timestamp: Date.now() });
                      window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
                    }
                  })
                  .catch((error) => {
                    console.error('移動文件失敗:', error);
                    setNotification({ message: '移動文件失敗', type: 'error' });
                    setTimeout(() => setNotification(null), 3000);
                  });
              }
            }
          });
        }
      }

      // Cmd/Ctrl + A: 全選當前資料夾中的所有文件
      if ((e.metaKey || e.ctrlKey) && e.key === 'a') {
        e.preventDefault();
        // 獲取當前任務的所有文件ID
        if (treeData?.data?.tree) {
          const allFileIds: string[] = [];
          Object.values(treeData.data.tree).forEach((files: any[]) => {
            files.forEach((file: any) => {
              allFileIds.push(file.file_id);
            });
          });
          batchSelection.selectAll(allFileIds);
          setNotification({ message: `已選擇 ${allFileIds.length} 個文件`, type: 'success' });
          setTimeout(() => setNotification(null), 3000);
        }
      }

      // ↑/↓: 在文件列表中上下移動選擇
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        // 實現鍵盤導航（需要構建文件列表）
        // 這裡簡化實現，實際應該根據當前視圖構建列表
      }

      // Enter: 打開選中的文件或展開/折疊資料夾
      if (e.key === 'Enter' && selectedFileId) {
        e.preventDefault();
        if (onFileSelect) {
          onFileSelect(selectedFileId);
        }
      }

      // ←: 折疊當前資料夾
      if (e.key === 'ArrowLeft' && selectedTaskId) {
        e.preventDefault();
        if (expandedTasks.has(selectedTaskId)) {
          toggleTask(selectedTaskId);
        }
      }

      // →: 展開當前資料夾
      if (e.key === 'ArrowRight' && selectedTaskId) {
        e.preventDefault();
        if (!expandedTasks.has(selectedTaskId)) {
          toggleTask(selectedTaskId);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [
    selectedFileId,
    selectedTaskId,
    contextMenu,
    folderContextMenu,
    expandedTasks,
    treeData,
    focusedFolderId,
    taskId,
    onFileSelect,
    toggleTask,
    setClipboard,
    batchSelection,
  ]);

  // 處理文件右鍵菜單
  const handleContextMenu = useCallback((e: React.MouseEvent, fileId: string, fileName: string) => {
    e.preventDefault();
    e.stopPropagation();

    // 關閉資料夾菜單（如果打開）
    setFolderContextMenu(null);

    // 計算菜單位置，確保不會超出視窗邊界
    const menuWidth = 180; // 菜單寬度
    const menuHeight = 280; // 預估菜單高度
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 10);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 10);

    setContextMenu({
      x: Math.max(10, x),
      y: Math.max(10, y),
      fileId,
      fileName,
    });
  }, []);

  // 處理資料夾右鍵菜單
  const handleFolderContextMenu = useCallback((e: React.MouseEvent, taskId: string, taskName: string) => {
    e.preventDefault();
    e.stopPropagation();

    // 關閉文件菜單（如果打開）
    setContextMenu(null);

    // 計算菜單位置，確保不會超出視窗邊界
    const menuWidth = 180; // 菜單寬度
    const menuHeight = 240; // 預估菜單高度
    const x = Math.min(e.clientX, window.innerWidth - menuWidth - 10);
    const y = Math.min(e.clientY, window.innerHeight - menuHeight - 10);

    setFolderContextMenu({
      x: Math.max(10, x),
      y: Math.max(10, y),
      taskId,
      taskName,
    });
  }, []);

  // 關閉右鍵菜單
  const closeContextMenu = useCallback(() => {
    setContextMenu(null);
  }, []);

  // 關閉資料夾右鍵菜單
  const closeFolderContextMenu = useCallback(() => {
    setFolderContextMenu(null);
  }, []);

  // 點擊外部關閉右鍵菜單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
        closeContextMenu();
      }
      if (folderContextMenuRef.current && !folderContextMenuRef.current.contains(event.target as Node)) {
        closeFolderContextMenu();
      }
    };

    if (contextMenu || folderContextMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [contextMenu, folderContextMenu, closeContextMenu, closeFolderContextMenu]);

  // 處理文件菜單項點擊
  const handleMenuAction = useCallback((action: string) => {
    if (!contextMenu) {
      console.warn('[FileTree] handleMenuAction called but contextMenu is null');
      return;
    }


    switch (action) {
      case 'rename':
        // 實現重新命名文件功能
        // 確保文件 ID 不是 temp-workspace（文件 ID 不應該是 temp-workspace，但為了安全起見還是檢查）
        if (contextMenu.fileId === TEMP_WORKSPACE_ID) {
          console.error('[FileTree] Invalid: fileId is temp-workspace, this should not happen');
          setNotification({ message: '無法重命名此文件', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
          break;
        }
        setRenameTarget({ id: contextMenu.fileId, name: contextMenu.fileName, type: 'file' });
        setRenameInput(contextMenu.fileName);
        setShowRenameModal(true);
        break;
      case 'move':
        // TODO: 實現移動目錄功能
        // TODO: 實現移動目錄功能
        break;
      case 'delete':
        // TODO: 實現刪除文件功能
        // TODO: 實現刪除文件功能
        break;
      case 'copy':
        // TODO: 實現複製功能
        // TODO: 實現複製功能
        break;
      case 'copyPath':
        // 實現複製路徑功能
        // 從 treeData 中查找文件所屬的 task_id
        let fileTaskId: string | null = null;
        if (treeData?.data?.tree) {
          for (const [taskId, files] of Object.entries(treeData.data.tree)) {
            if (files.some((f: any) => f.file_id === contextMenu.fileId)) {
              fileTaskId = taskId;
              break;
            }
          }
        }

        // 構建文件路徑字符串
        const filePath = fileTaskId
          ? `${fileTaskId}/${contextMenu.fileId}`
          : contextMenu.fileId;

        // 複製到剪貼板
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(filePath)
            .then(() => {
              setNotification({ message: '文件路徑已複製到剪貼板', type: 'success' });
              setTimeout(() => setNotification(null), 3000);
            })
            .catch((err) => {
              console.error('複製路徑失敗:', err);
              setNotification({ message: '複製路徑失敗，請手動複製', type: 'error' });
              setTimeout(() => setNotification(null), 3000);
            });
        } else {
          // 瀏覽器不支持剪貼板API，使用 fallback 方法
          const textArea = document.createElement('textarea');
          textArea.value = filePath;
          textArea.style.position = 'fixed';
          textArea.style.opacity = '0';
          document.body.appendChild(textArea);
          textArea.select();
          try {
            document.execCommand('copy');
            setNotification({ message: '文件路徑已複製到剪貼板', type: 'success' });
            setTimeout(() => setNotification(null), 3000);
          } catch (err) {
            console.error('複製路徑失敗:', err);
            setNotification({ message: '複製路徑失敗，請手動複製', type: 'error' });
            setTimeout(() => setNotification(null), 3000);
          }
          document.body.removeChild(textArea);
        }
        break;
      case 'cut':
        // TODO: 實現剪下功能
        // TODO: 實現剪下功能
        break;
      case 'paste':
        // TODO: 實現貼上功能
        // TODO: 實現貼上功能
        break;
      case 'attachToChat':
        // TODO: 實現標註到AI任務指令區功能
        // TODO: 實現標註到AI任務指令區功能
        break;
      case 'viewVectors':
        // TODO: 實現查看向量資料功能
        // TODO: 實現查看向量資料功能
        break;
      case 'viewGraph':
        // TODO: 實現查看圖譜資料功能
        // TODO: 實現查看圖譜資料功能
        break;
      case 'fileInfo':
        // 顯示文件信息對話框
        setFileInfo({ fileId: contextMenu.fileId, fileName: contextMenu.fileName });
        setShowFileInfoModal(true);
        break;
      default:
        break;
    }

    closeContextMenu();
  }, [contextMenu, closeContextMenu]);

  // 處理資料夾菜單項點擊
  const handleFolderMenuAction = useCallback((action: string) => {
    if (!folderContextMenu) {
      console.warn('[FileTree] handleFolderMenuAction called but folderContextMenu is null');
      return;
    }


    switch (action) {
      case 'newFolder':
        // 實現新增資料夾功能
        // 打開新增資料夾對話框
        // 注意：即使是 temp-workspace，也應該傳遞給後端作為 parent_task_id
        setNewFolderParentId(folderContextMenu.taskId);
        setNewFolderInput('');
        setShowNewFolderModal(true);
        break;
      case 'newFile':
        // 實現新增檔案功能：觸發父組件的回調
        if (onNewFile) {
          onNewFile(folderContextMenu.taskId);
        } else {
        // TODO: 實現新增檔案功能
        }
        break;
      case 'copyPath':
        // 複製資料夾路徑到剪貼板
        const folderPath = folderContextMenu.taskId;

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(folderPath)
            .then(() => {
              setNotification({ message: '資料夾路徑已複製到剪貼板', type: 'success' });
              setTimeout(() => setNotification(null), 3000);
            })
            .catch((err) => {
              console.error('複製路徑失敗:', err);
              setNotification({ message: '複製路徑失敗，請手動複製', type: 'error' });
              setTimeout(() => setNotification(null), 3000);
            });
        } else {
          // 瀏覽器不支持剪貼板API，使用 fallback 方法
          const textArea = document.createElement('textarea');
          textArea.value = folderPath;
          textArea.style.position = 'fixed';
          textArea.style.opacity = '0';
          document.body.appendChild(textArea);
          textArea.select();
          try {
            document.execCommand('copy');
            setNotification({ message: '資料夾路徑已複製到剪貼板', type: 'success' });
            setTimeout(() => setNotification(null), 3000);
          } catch (err) {
            console.error('複製路徑失敗:', err);
            setNotification({ message: '複製路徑失敗，請手動複製', type: 'error' });
            setTimeout(() => setNotification(null), 3000);
          }
          document.body.removeChild(textArea);
        }
        break;
      case 'info':
        // TODO: 實現資料夾信息功能
        // TODO: 實現查看資料夾信息功能
        break;
      case 'cut':
        // TODO: 實現剪下功能
        // TODO: 實現剪下資料夾功能
        break;
      case 'paste':
        // TODO: 實現貼上功能
        // TODO: 實現貼上到資料夾功能
        break;
      case 'rename':
        // 檢查是否為 temp-workspace（不允許重命名）
          taskId: folderContextMenu.taskId,
          taskName: folderContextMenu.taskName,
          isTempWorkspace: folderContextMenu.taskId === TEMP_WORKSPACE_ID,
          TEMP_WORKSPACE_ID: TEMP_WORKSPACE_ID,
          type: 'FOLDER (not file)'
        });
        if (folderContextMenu.taskId === TEMP_WORKSPACE_ID) {
          console.warn('[FileTree] Attempted to rename temp-workspace folder - BLOCKED', {
            taskId: folderContextMenu.taskId,
            taskName: folderContextMenu.taskName
          });
          setNotification({
            message: '任務工作區是系統預設的工作區，無法重命名。如需重命名任務，請選擇其他任務文件夾。',
            type: 'error'
          });
          setTimeout(() => setNotification(null), 5000);
          break;
        }
        // 打開重命名對話框
          id: folderContextMenu.taskId,
          name: folderContextMenu.taskName,
          type: 'folder'
        });
        setRenameTarget({ id: folderContextMenu.taskId, name: folderContextMenu.taskName, type: 'folder' });
        setRenameInput(folderContextMenu.taskName);
        setShowRenameModal(true);
        break;
      case 'delete':
        // 實現刪除資料夾功能
        // 檢查是否是 temp-workspace，如果是則不允許刪除
        if (folderContextMenu.taskId === TEMP_WORKSPACE_ID) {
          setNotification({ message: '任務工作區是系統預設的工作區，無法刪除。', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
          break;
        }
        // 打開刪除確認對話框
        setDeleteFolderTarget({
          taskId: folderContextMenu.taskId,
          taskName: folderContextMenu.taskName,
        });
        setShowDeleteFolderModal(true);
        break;
      default:
        break;
    }

    closeFolderContextMenu();
  }, [folderContextMenu, closeFolderContextMenu, onNewFile]);

  const loadTree = useCallback(async () => {
    // 如果已經有 fileTree prop，不調用 API（使用本地數據）
    if (fileTree && fileTree.length > 0) {
      setTreeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    // 如果沒有任務 ID，不調用 API
    if (!taskId) {
      setTreeData(null);
      setLoading(false);
      return;
    }

    // 檢查是否有模擬文件（歷史任務）
    if (hasMockFiles(taskId)) {
      setLoading(true);
      setError(null);
      try {
        const mockFiles = getMockFiles(taskId);
        // 將模擬文件轉換為 FileTreeResponse 格式
        const mockResponse: FileTreeResponse = {
          success: true,
          data: {
            tree: {
              [taskId]: mockFiles.map(file => ({
                file_id: file.file_id,
                filename: file.filename,
                file_type: file.file_type,
                file_size: file.file_size,
                user_id: file.user_id,
                task_id: file.task_id,
                upload_time: file.upload_time,
              })),
            },
            total_tasks: 1,
            total_files: mockFiles.length,
          },
        };
        setTreeData(mockResponse);
      } catch (err: any) {
        setError(err.message || '加載模擬文件失敗');
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const startTime = Date.now();
      const response = await Promise.race([
        getFileTree({ user_id: userId, task_id: taskId }),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('API request timeout after 30 seconds')), 30000)
        )
      ]) as any;
      if (response.success && response.data) {
        setTreeData(response);
      } else {
        console.error('[FileTree] Failed to load file tree:', response);
        setError('無法加載文件樹');
      }
    } catch (err: any) {
      console.error('[FileTree] Error loading file tree:', err);
      console.error('[FileTree] Error details:', {
        message: err.message,
        stack: err.stack,
        name: err.name
      });
      // 超时错误应该显示给用户，而不是隐藏
      if (err.message?.includes('timeout')) {
        console.error('[FileTree] API request timeout');
        setError('請求超時，請檢查網絡連接或稍後再試');
        setTreeData(null);
      } else if (err.message?.includes('Failed to fetch') ||
          err.message?.includes('ERR_CONNECTION_TIMED_OUT') ||
          err.message?.includes('NetworkError')) {
        console.warn('[FileTree] Connection error');
        setError('無法連接到服務器，請確認後端服務是否正在運行');
        setTreeData(null);
      } else {
        console.error('[FileTree] Other error:', err.message);
      setError(err.message || '加載文件樹失敗');
      }
    } finally {
      setLoading(false);
    }
  }, [userId, taskId, fileTree]);

  useEffect(() => {

    // 如果已經有 fileTree prop，直接返回，不調用 API
    if (fileTree && fileTree.length > 0) {
      setTreeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    // 如果沒有任務 ID，直接返回，不調用 loadTree
    if (!taskId) {
      setTreeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    loadTree();
  }, [loadTree, taskId, fileTree]);

  // 監聽文件樹更新事件
  useEffect(() => {
    const handleFileTreeUpdate = () => {
      // 如果 fileTree 是空數組或未定義，重新加載
      // 因為即使有 fileTree prop，如果它是空的，也需要刷新
      if (!fileTree || (Array.isArray(fileTree) && fileTree.length === 0)) {
        loadTree();
      } else {
      }
    };

    window.addEventListener('fileTreeUpdated', handleFileTreeUpdate);
    return () => {
      window.removeEventListener('fileTreeUpdated', handleFileTreeUpdate);
    };
  }, [loadTree, taskId, fileTree]);

  // 如果沒有任務 ID 且沒有 fileTree，顯示空白
  if (!taskId && (!fileTree || fileTree.length === 0)) {
    return (
      <div className="p-4 text-sm text-tertiary text-center theme-transition">
        暫無文件
        <br />
        <span className="text-xs text-muted theme-transition">開始輸入或上傳文件後將顯示文件目錄</span>
      </div>
    );
  }

  // 如果有 fileTree prop，優先使用它（不調用 API）
  if (fileTree && fileTree.length > 0) {
    // 遞歸渲染文件樹節點
    const renderFileNode = (node: FileNode, level: number = 0): React.ReactNode => {
      const isExpanded = expandedTasks.has(node.id);

      const handleFolderClick = () => {
        toggleTask(node.id);
      };

      if (node.type === 'folder') {
        return (
          <div key={node.id} className="mb-1">
            <div
              className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors theme-transition ${
                'hover:bg-tertiary text-primary'
              }`}
              style={{ paddingLeft: `${level * 1 + 0.5}rem` }}
              onClick={handleFolderClick}
            >
              <div
                className="p-0.5 hover:bg-hover rounded theme-transition flex-shrink-0 flex items-center justify-center"
                onClick={(e) => {
                  e.stopPropagation();
                  handleFolderClick();
                }}
              >
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-primary" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-primary" />
                )}
              </div>
              {isExpanded ? (
                <FolderOpen className="w-4 h-4 text-blue-500 flex-shrink-0" />
              ) : (
                <Folder className="w-4 h-4 text-tertiary flex-shrink-0" />
              )}
              <span className="flex-1 text-sm truncate text-primary">{node.name}</span>
              {node.children && node.children.length > 0 && (
                <span className="text-xs text-tertiary flex-shrink-0">{node.children.length}</span>
              )}
            </div>
            {isExpanded && node.children && node.children.length > 0 && (
              <div className="ml-2 mt-1">
                {node.children.map((child) => renderFileNode(child, level + 1))}
              </div>
            )}
          </div>
        );
      } else {
        return (
          <div
            key={node.id}
            className="flex items-center gap-2 px-2 py-1 text-xs text-secondary hover:bg-tertiary rounded cursor-pointer theme-transition"
            style={{ paddingLeft: `${level * 1 + 1.5}rem` }}
            onClick={() => {
              if (onFileSelect) {
                onFileSelect(node.id, node.name);
              }
            }}
          >
            <FileIcon className="w-3 h-3 text-tertiary" />
            <span className="flex-1 truncate text-primary">{node.name}</span>
          </div>
        );
      }
    };

    return (
      <div className="h-full overflow-y-auto">
        <div className="p-4 border-b border-primary theme-transition">
          <h3 className="text-sm font-semibold text-primary mb-1 theme-transition">文件目錄</h3>
          <p className="text-xs text-tertiary theme-transition">
            本地任務文件
          </p>
        </div>
        <div className="p-2">
          {fileTree.map((node) => renderFileNode(node, 0))}
        </div>
      </div>
    );
  }


  const handleTaskClick = (taskId: string) => {
    if (onTaskSelect) {
      // 如果點擊已選中的任務，取消選擇（顯示所有文件）
      const newTaskId = selectedTaskId === taskId ? null : taskId;
      onTaskSelect(newTaskId);
    }

    // 滾動到被點擊的資料夾位置
    setTimeout(() => {
      const folderElement = folderRefs.current.get(taskId);
      if (folderElement) {
        folderElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        // 添加短暫的 focus 效果
        folderElement.focus();
      }
    }, 100);
  };

  if (loading) {
    return (
      <div className="p-4 text-sm text-tertiary theme-transition">
        加載中...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-sm text-red-500 theme-transition">
        {error}
      </div>
    );
  }

  if (!treeData || !treeData.data) {
    return (
      <div className="p-4 text-sm text-tertiary theme-transition">
        暫無文件
      </div>
    );
  }

  const { tree, total_tasks, total_files, folders } = treeData.data;
  const foldersInfo = folders || {};

  // 構建任務列表（優先顯示任務工作區）
  const taskList: TreeNode[] = [];

  // 首先添加任務工作區（如果存在）
  if (tree[TEMP_WORKSPACE_ID]) {
    taskList.push({
      taskId: TEMP_WORKSPACE_ID,
      taskName: TEMP_WORKSPACE_NAME,
      fileCount: tree[TEMP_WORKSPACE_ID].length,
      isExpanded: expandedTasks.has(TEMP_WORKSPACE_ID),
    });
  } else {
    // 即使沒有文件，也顯示任務工作區（空目錄）
    taskList.push({
      taskId: TEMP_WORKSPACE_ID,
      taskName: TEMP_WORKSPACE_NAME,
      fileCount: 0,
      isExpanded: expandedTasks.has(TEMP_WORKSPACE_ID),
    });
  }

  // 如果指定了 taskId，只顯示任務工作區，不顯示其他任務文件夾
  // 這樣符合規劃：上傳的資料都放在任務id的上傳資料暫存區
  if (!taskId) {
    // 只有在沒有指定 taskId 時，才顯示其他任務文件夾
    // 包括：
    // 1. 頂級資料夾（parent_task_id 為 null 的資料夾，與任務工作區同級）
    // 2. 其他任務文件夾（在 folders 中但不在 temp-workspace 下的資料夾）
    const topLevelFolders = getTopLevelFolders();
    topLevelFolders.forEach((folder) => {
      if (folder.taskId !== TEMP_WORKSPACE_ID) {
        taskList.push(folder);
      }
    });

    // 顯示其他任務文件夾（不在 folders 中的，可能是舊的任務ID）
    Object.entries(tree).forEach(([taskIdKey, files]) => {
      if (taskIdKey !== TEMP_WORKSPACE_ID && !foldersInfo[taskIdKey]) {
        taskList.push({
          taskId: taskIdKey,
          taskName: taskIdKey,
          fileCount: files.length,
          isExpanded: expandedTasks.has(taskIdKey),
        });
      }
    });
  }

  // 獲取子資料夾列表（用於在 temp-workspace 或其他資料夾下顯示）
  const getSubFolders = (parentTaskId: string): TreeNode[] => {
    const subFolders: TreeNode[] = [];
    Object.entries(foldersInfo).forEach(([folderTaskId, folderInfo]) => {
      // 處理 parent_task_id 可能為 null、undefined 或字符串的情況
      const folderParentId = folderInfo.parent_task_id;
      // 匹配邏輯：
      // 1. 如果 folderParentId === parentTaskId，直接匹配
      // 2. 如果 folderParentId 是 null/undefined 且 parentTaskId 是 TEMP_WORKSPACE_ID，匹配（頂級資料夾顯示在暫存工作區下）
      const isMatch = folderParentId === parentTaskId ||
                      ((folderParentId === null || folderParentId === undefined) && parentTaskId === TEMP_WORKSPACE_ID);
        folderTaskId,
        folderInfo,
        folderParentId,
        parentTaskId,
        isMatch,
        folderParentIdType: typeof folderParentId,
        parentTaskIdType: typeof parentTaskId
      });
      if (isMatch) {
        subFolders.push({
          taskId: folderTaskId,
          taskName: folderInfo.folder_name,
          fileCount: tree[folderTaskId]?.length || 0,
          isExpanded: expandedTasks.has(folderTaskId),
        });
      }
    });
    return subFolders;
  };

  // 獲取頂級資料夾列表（parent_task_id 為 null 的資料夾，與暫存工作區同級）
  const getTopLevelFolders = (): TreeNode[] => {
    const topLevelFolders: TreeNode[] = [];
    Object.entries(foldersInfo).forEach(([folderTaskId, folderInfo]) => {
      // 頂級資料夾：parent_task_id 為 null 或 undefined
      if (folderInfo.parent_task_id === null || folderInfo.parent_task_id === undefined) {
        topLevelFolders.push({
          taskId: folderTaskId,
          taskName: folderInfo.folder_name,
          fileCount: tree[folderTaskId]?.length || 0,
          isExpanded: expandedTasks.has(folderTaskId),
        });
      }
    });
    return topLevelFolders;
  };

  return (
    <div className="h-full overflow-y-auto" ref={fileTreeRef} tabIndex={0}>
      <div className="p-4 border-b border-primary theme-transition">
        <h3 className="text-sm font-semibold text-primary mb-1 theme-transition">文件目錄</h3>
        <p className="text-xs text-tertiary theme-transition">
          {total_tasks} 個工作區 • {total_files} 個文件
        </p>
      </div>

      <div className="p-2">
        {taskList.map((task) => {
          const isSelected = selectedTaskId === task.taskId;
          const isExpanded = expandedTasks.has(task.taskId);
          const files = tree[task.taskId] || [];

          return (
            <div key={task.taskId} className="mb-1">
              {/* 任務節點 */}
              <div
                ref={(el) => {
                  if (el) {
                    folderRefs.current.set(task.taskId, el);
                  } else {
                    folderRefs.current.delete(task.taskId);
                  }
                }}
                tabIndex={0}
                className={`flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-all duration-200 theme-transition focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-1 ${
                  isSelected
                    ? 'bg-blue-500/30 text-blue-300 border-l-4 border-blue-500 shadow-md'
                    : 'hover:bg-blue-500/25 hover:text-blue-300 hover:border-l-4 hover:border-blue-500 hover:shadow-md text-primary'
                }`}
                onClick={() => {
                  handleTaskClick(task.taskId);
                  // 設置聚焦狀態
                  setFocusedFolderId(task.taskId);
                  // 通知父組件當前聚焦的資料夾
                  if (onFolderFocus) {
                    onFolderFocus(task.taskId);
                  }
                }}
                onContextMenu={(e) => {
                  handleFolderContextMenu(e, task.taskId, task.taskName);
                  // 設置聚焦狀態
                  setFocusedFolderId(task.taskId);
                  // 右鍵時也設置聚焦
                  if (onFolderFocus) {
                    onFolderFocus(task.taskId);
                  }
                }}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleTask(task.taskId);
                  }}
                  className="p-0.5 hover:bg-hover rounded theme-transition"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-primary" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-primary" />
                  )}
                </button>
                {isExpanded ? (
                  <FolderOpen className="w-4 h-4 text-blue-500" />
                ) : (
                  <Folder className="w-4 h-4 text-tertiary" />
                )}
                <span className="flex-1 text-sm truncate text-primary">
                  {task.taskName}
                </span>
                <span className="text-xs text-tertiary">
                  {task.fileCount}
                </span>
              </div>

              {/* 子資料夾列表（展開時顯示） */}
              {isExpanded && (() => {
                const subFolders = getSubFolders(task.taskId);
                if (subFolders.length === 0) return null;
                return (
                  <div className="ml-6 mt-1 space-y-0.5">
                    {subFolders.map((subFolder) => {
                      const isSubExpanded = expandedTasks.has(subFolder.taskId);
                      const subFiles = tree[subFolder.taskId] || [];
                      return (
                        <div key={subFolder.taskId} className="mb-1">
                          <div
                            ref={(el) => {
                              if (el) {
                                folderRefs.current.set(subFolder.taskId, el);
                              } else {
                                folderRefs.current.delete(subFolder.taskId);
                              }
                            }}
                            tabIndex={0}
                            className={`flex items-center gap-2 px-2 py-1 text-xs rounded cursor-pointer transition-all duration-200 theme-transition focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-1 ${
                              selectedTaskId === subFolder.taskId
                                ? 'bg-blue-500/30 text-blue-300 border-l-4 border-blue-500 shadow-md'
                                : 'hover:bg-blue-500/25 hover:text-blue-300 hover:border-l-4 hover:border-blue-500 hover:shadow-md text-primary'
                            }`}
                            onClick={() => {
                              handleTaskClick(subFolder.taskId);
                              setFocusedFolderId(subFolder.taskId);
                              if (onFolderFocus) {
                                onFolderFocus(subFolder.taskId);
                              }
                            }}
                            onContextMenu={(e) => {
                              handleFolderContextMenu(e, subFolder.taskId, subFolder.taskName);
                              setFocusedFolderId(subFolder.taskId);
                              if (onFolderFocus) {
                                onFolderFocus(subFolder.taskId);
                              }
                            }}
                          >
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleTask(subFolder.taskId);
                              }}
                              className="p-0.5 hover:bg-hover rounded theme-transition"
                            >
                              {isSubExpanded ? (
                                <ChevronDown className="w-3 h-3 text-primary" />
                              ) : (
                                <ChevronRight className="w-3 h-3 text-primary" />
                              )}
                            </button>
                            {isSubExpanded ? (
                              <FolderOpen className="w-3 h-3 text-blue-500 flex-shrink-0" />
                            ) : (
                              <Folder className="w-3 h-3 text-tertiary flex-shrink-0" />
                            )}
                            <span className="flex-1 text-xs truncate text-primary">{subFolder.taskName}</span>
                            <span className="text-xs text-tertiary flex-shrink-0">{subFiles.length}</span>
                          </div>
                          {/* 子資料夾的子資料夾列表（支持嵌套） */}
                          {isSubExpanded && (() => {
                            const subSubFolders = getSubFolders(subFolder.taskId);
                            if (subSubFolders.length > 0) {
                              return (
                                <div className="ml-6 mt-1 space-y-0.5">
                                  {subSubFolders.map((subSubFolder) => {
                                    const isSubSubExpanded = expandedTasks.has(subSubFolder.taskId);
                                    const subSubFiles = tree[subSubFolder.taskId] || [];
                                    return (
                                      <div key={subSubFolder.taskId} className="mb-1">
                                        <div
                                          ref={(el) => {
                                            if (el) {
                                              folderRefs.current.set(subSubFolder.taskId, el);
                                            } else {
                                              folderRefs.current.delete(subSubFolder.taskId);
                                            }
                                          }}
                                          tabIndex={0}
                                          className={`flex items-center gap-2 px-2 py-1 text-xs rounded cursor-pointer transition-all duration-200 theme-transition focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:ring-offset-1 ${
                                            selectedTaskId === subSubFolder.taskId
                                              ? 'bg-blue-500/30 text-blue-300 border-l-4 border-blue-500 shadow-md'
                                              : 'hover:bg-blue-500/25 hover:text-blue-300 hover:border-l-4 hover:border-blue-500 hover:shadow-md text-primary'
                                          }`}
                                          onClick={() => {
                                            handleTaskClick(subSubFolder.taskId);
                                            setFocusedFolderId(subSubFolder.taskId);
                                            if (onFolderFocus) {
                                              onFolderFocus(subSubFolder.taskId);
                                            }
                                          }}
                                          onContextMenu={(e) => {
                                            handleFolderContextMenu(e, subSubFolder.taskId, subSubFolder.taskName);
                                            setFocusedFolderId(subSubFolder.taskId);
                                            if (onFolderFocus) {
                                              onFolderFocus(subSubFolder.taskId);
                                            }
                                          }}
                                        >
                                          <button
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              toggleTask(subSubFolder.taskId);
                                            }}
                                            className="p-0.5 hover:bg-hover rounded theme-transition"
                                          >
                                            {isSubSubExpanded ? (
                                              <ChevronDown className="w-3 h-3 text-primary" />
                                            ) : (
                                              <ChevronRight className="w-3 h-3 text-primary" />
                                            )}
                                          </button>
                                          {isSubSubExpanded ? (
                                            <FolderOpen className="w-3 h-3 text-blue-500 flex-shrink-0" />
                                          ) : (
                                            <Folder className="w-3 h-3 text-tertiary flex-shrink-0" />
                                          )}
                                          <span className="flex-1 text-xs truncate text-primary">{subSubFolder.taskName}</span>
                                          <span className="text-xs text-tertiary flex-shrink-0">{subSubFiles.length}</span>
                                        </div>
                                        {/* 子資料夾的文件列表 */}
                                        {isSubSubExpanded && subSubFiles.length > 0 && (
                                          <div className="ml-6 mt-1 space-y-0.5">
                                            {subSubFiles.slice(0, 10).map((file: any) => (
                                              <div
                                                key={file.file_id}
                                                className={`flex items-center gap-2 px-2 py-1 text-xs rounded cursor-pointer transition-all duration-200 theme-transition ${
                                                  selectedFileId === file.file_id
                                                    ? 'bg-blue-500/30 text-blue-300 border-l-4 border-blue-500 shadow-md'
                                                    : 'text-secondary hover:bg-blue-500/25 hover:text-blue-300 hover:border-l-4 hover:border-blue-500 hover:shadow-md'
                                                }`}
                                                onClick={() => {
                                                  setSelectedFileId(file.file_id);
                                                  if (onFileSelect) {
                                                    onFileSelect(file.file_id, file.filename);
                                                  }
                                                }}
                                                onContextMenu={(e) => {
                                                  handleContextMenu(e, file.file_id, file.filename);
                                                }}
                                              >
                                                <FileIcon className="w-3 h-3 text-tertiary flex-shrink-0" />
                                                <span className={`flex-1 truncate ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-primary'}`}>{file.filename}</span>
                                              </div>
                                            ))}
                                            {subSubFiles.length > 10 && (
                                              <div className="px-2 py-1 text-xs text-tertiary theme-transition">
                                                ...還有 {subSubFiles.length - 10} 個文件
                                              </div>
                                            )}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              );
                            }
                            return null;
                          })()}
                          {/* 子資料夾的文件列表 */}
                          {isSubExpanded && subFiles.length > 0 && (
                            <div className="ml-6 mt-1 space-y-0.5">
                              {subFiles.slice(0, 10).map((file: any) => (
                                <div
                                  key={file.file_id}
                                  className={`flex items-center gap-2 px-2 py-1 text-xs rounded cursor-pointer transition-all duration-200 theme-transition ${
                                    selectedFileId === file.file_id
                                      ? 'bg-blue-500/30 text-blue-300 border-l-4 border-blue-500 shadow-md'
                                      : 'text-secondary hover:bg-blue-500/25 hover:text-blue-300 hover:border-l-4 hover:border-blue-500 hover:shadow-md'
                                  }`}
                                  onClick={() => {
                                    setSelectedFileId(file.file_id);
                                    if (onFileSelect) {
                                      onFileSelect(file.file_id, file.filename);
                                    }
                                  }}
                                  onContextMenu={(e) => {
                                    handleContextMenu(e, file.file_id, file.filename);
                                  }}
                                >
                                  <FileIcon className="w-3 h-3 text-tertiary flex-shrink-0" />
                                  <span className={`flex-1 truncate ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-primary'}`}>{file.filename}</span>
                                </div>
                              ))}
                              {subFiles.length > 10 && (
                                <div className="px-2 py-1 text-xs text-tertiary theme-transition">
                                  ...還有 {subFiles.length - 10} 個文件
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                );
              })()}

              {/* 文件列表（展開時顯示） */}
              {isExpanded && files.length > 0 && (
                <div className="ml-6 mt-1 space-y-0.5">
                  {files.slice(0, 10).map((file) => (
                    <div
                      key={file.file_id}
                      className={`flex items-center gap-2 px-2 py-1 text-xs rounded cursor-pointer transition-all duration-200 theme-transition ${
                        selectedFileId === file.file_id
                          ? 'bg-blue-500/30 text-blue-300 border-l-4 border-blue-500 shadow-md'
                          : 'text-secondary hover:bg-blue-500/25 hover:text-blue-300 hover:border-l-4 hover:border-blue-500 hover:shadow-md'
                      }`}
                      onClick={() => {
                        setSelectedFileId(file.file_id);
                        if (onFileSelect) {
                          // 傳遞 file_id 和 filename，確保能正確識別文件
                          onFileSelect(file.file_id, file.filename);
                        }
                      }}
                      onContextMenu={(e) => handleContextMenu(e, file.file_id, file.filename)}
                    >
                      <FileIcon className={`w-3 h-3 ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-tertiary'}`} />
                      <span className={`flex-1 truncate ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-primary'}`}>{file.filename}</span>
                    </div>
                  ))}
                  {files.length > 10 && (
                    <div className="px-2 py-1 text-xs text-tertiary theme-transition">
                      ...還有 {files.length - 10} 個文件
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 右鍵菜單 */}
      {contextMenu && (
        <div
          ref={contextMenuRef}
          className="fixed z-50 bg-secondary border border-primary rounded-lg shadow-lg py-1 min-w-[180px] theme-transition"
          style={{
            left: `${contextMenu.x}px`,
            top: `${contextMenu.y}px`,
          }}
        >
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('rename')}
          >
            <i className="fa-solid fa-pen w-4"></i>
            <span>重新命名</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('move')}
          >
            <i className="fa-solid fa-folder-open w-4"></i>
            <span>移動目錄</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-red-500/20 hover:text-red-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('delete')}
          >
            <i className="fa-solid fa-trash w-4"></i>
            <span>刪除文件</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('copy')}
          >
            <i className="fa-solid fa-copy w-4"></i>
            <span>複製</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('copyPath')}
          >
            <i className="fa-solid fa-link w-4"></i>
            <span>複製路徑</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('cut')}
          >
            <i className="fa-solid fa-cut w-4"></i>
            <span>剪下</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('paste')}
          >
            <i className="fa-solid fa-paste w-4"></i>
            <span>貼上</span>
          </button>
          <div className="border-t border-primary my-1"></div>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('attachToChat')}
          >
            <i className="fa-solid fa-paperclip w-4"></i>
            <span>標註到AI任務指令區</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('viewVectors')}
          >
            <i className="fa-solid fa-database w-4"></i>
            <span>查看向量資料</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('viewGraph')}
          >
            <i className="fa-solid fa-project-diagram w-4"></i>
            <span>查看圖譜資料</span>
          </button>
          <div className="border-t border-primary my-1"></div>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('fileInfo')}
          >
            <i className="fa-solid fa-info-circle w-4"></i>
            <span>查看文件信息</span>
          </button>
        </div>
      )}

      {/* 文件信息對話框 */}
      {showFileInfoModal && fileInfo && (
        <FileInfoModal
          fileId={fileInfo.fileId}
          fileName={fileInfo.fileName}
          taskId={taskId}
          onClose={() => {
            setShowFileInfoModal(false);
            setFileInfo(null);
          }}
        />
      )}

      {/* 重命名對話框 */}
      {showRenameModal && renameTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              重命名{renameTarget.type === 'folder' ? '資料夾' : '文件'}
            </h2>
            <input
              ref={renameInputRef}
              type="text"
              value={renameInput}
              onChange={(e) => setRenameInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleRenameConfirm();
                } else if (e.key === 'Escape') {
                  handleRenameCancel();
                }
              }}
              className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition mb-4"
              placeholder="請輸入新名稱"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={handleRenameCancel}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleRenameConfirm}
                disabled={!renameInput.trim() || renameInput.trim() === renameTarget.name}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                確定
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 新增資料夾對話框 */}
      {showNewFolderModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              新增資料夾
            </h2>
            <input
              ref={newFolderInputRef}
              type="text"
              value={newFolderInput}
              onChange={(e) => setNewFolderInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleNewFolderConfirm();
                } else if (e.key === 'Escape') {
                  handleNewFolderCancel();
                }
              }}
              className="w-full px-4 py-2 bg-tertiary border border-primary rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition mb-4"
              placeholder="請輸入資料夾名稱"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={handleNewFolderCancel}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleNewFolderConfirm}
                disabled={!newFolderInput.trim()}
                className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                確定
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 刪除資料夾確認對話框 */}
      {showDeleteFolderModal && deleteFolderTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              刪除資料夾
            </h2>
            <p className="text-sm text-tertiary mb-6 theme-transition">
              確定要刪除資料夾「<span className="text-primary font-semibold">{deleteFolderTarget.taskName}</span>」嗎？
              <br />
              <span className="text-red-400">此操作將永久刪除該資料夾及其下的所有文件，且無法復原。</span>
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={handleDeleteFolderCancel}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleDeleteFolderConfirm}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
              >
                確定刪除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 通知提示 */}
      {notification && (
        <div
          className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg theme-transition ${
            notification.type === 'success'
              ? 'bg-green-500/90 text-white'
              : 'bg-red-500/90 text-white'
          }`}
          style={{ animation: 'fadeIn 0.3s ease-in' }}
        >
          <div className="flex items-center gap-2">
            <i
              className={`fa-solid ${
                notification.type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'
              }`}
            ></i>
            <span className="text-sm font-medium">{notification.message}</span>
          </div>
        </div>
      )}

      {/* 資料夾右鍵菜單 */}
      {folderContextMenu && (
        <div
          ref={folderContextMenuRef}
          className="fixed z-50 bg-secondary border border-primary rounded-lg shadow-lg py-1 min-w-[180px] theme-transition"
          style={{
            left: `${folderContextMenu.x}px`,
            top: `${folderContextMenu.y}px`,
          }}
        >
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('newFolder')}
          >
            <i className="fa-solid fa-folder-plus w-4"></i>
            <span>新增資料夾</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('newFile')}
          >
            <i className="fa-solid fa-file-plus w-4"></i>
            <span>新增檔案</span>
          </button>
          <div className="border-t border-primary my-1"></div>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('copyPath')}
          >
            <i className="fa-solid fa-link w-4"></i>
            <span>複製資料夾路徑</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('info')}
          >
            <i className="fa-solid fa-info-circle w-4"></i>
            <span>資料夾信息</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('cut')}
          >
            <i className="fa-solid fa-cut w-4"></i>
            <span>剪下</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('paste')}
          >
            <i className="fa-solid fa-paste w-4"></i>
            <span>貼上</span>
          </button>
          <div className="border-t border-primary my-1"></div>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('rename')}
          >
            <i className="fa-solid fa-pen w-4"></i>
            <span>資料夾重命名</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/20 hover:text-red-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleFolderMenuAction('delete')}
          >
            <i className="fa-solid fa-trash w-4"></i>
            <span>刪除資料夾</span>
          </button>
        </div>
      )}
    </div>
  );
}

// 文件信息對話框組件
interface FileInfoModalProps {
  fileId: string;
  fileName: string;
  taskId?: string;
  onClose: () => void;
}

function FileInfoModal({ fileId, fileName, taskId, onClose }: FileInfoModalProps) {
  const [fileMetadata, setFileMetadata] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [hasVectors, setHasVectors] = useState<boolean | null>(null);
  const [hasGraph, setHasGraph] = useState<boolean | null>(null);

  useEffect(() => {
    const loadFileInfo = async () => {
      setLoading(true);
      try {
        // 優先從模擬存儲中獲取文件信息
        if (taskId) {
          const mockFile = getMockFile(String(taskId), fileId);
          if (mockFile) {
            setFileMetadata({
              file_id: mockFile.file_id,
              filename: mockFile.filename,
              file_type: mockFile.file_type,
              file_size: mockFile.file_size,
              upload_time: mockFile.upload_time,
              task_id: mockFile.task_id,
              user_id: mockFile.user_id,
            });
            setHasVectors(false); // 模擬文件暫時不檢查向量
            setHasGraph(false); // 模擬文件暫時不檢查圖譜
            setLoading(false);
            return;
          }
        }

        // 從後端 API 獲取文件信息
        try {
          // 嘗試通過 file_id 直接查詢（如果 API 支持）
          const response = await getFileList({ limit: 1000 });
          if (response.success && response.data?.files) {
            const file = response.data.files.find((f: any) => f.file_id === fileId);
            if (file) {
              setFileMetadata(file);
              // 檢查向量和圖譜數據狀態
              // 從文件元數據中獲取狀態
              if (file.vector_count !== undefined && file.vector_count > 0) {
                setHasVectors(true);
              } else if (file.processing_status === 'completed' || file.status === 'processed') {
                // 如果處理狀態為已完成，但沒有向量計數，可能還在處理中
                setHasVectors(null);
              } else {
                setHasVectors(false);
              }

              if (file.kg_status === 'completed' || file.kg_status === 'extracted') {
                setHasGraph(true);
              } else if (file.processing_status === 'completed' || file.status === 'processed') {
                setHasGraph(null);
              } else {
                setHasGraph(false);
              }
            }
          }
        } catch (error) {
          console.error('Failed to load file info:', error);
        }
      } finally {
        setLoading(false);
      }
    };

    loadFileInfo();
  }, [fileId, taskId]);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
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

  const getCurrentPath = (): string => {
    if (taskId) {
      return taskId === TEMP_WORKSPACE_ID ? '暫存工作區' : `任務: ${taskId}`;
    }
    return fileMetadata?.task_id || '未知路徑';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition" onClick={onClose}>
      <div
        className="bg-secondary border border-primary rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 標題欄 */}
        <div className="flex items-center justify-between p-4 border-b border-primary">
          <h2 className="text-lg font-semibold text-primary">文件信息</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-tertiary text-primary transition-colors"
            aria-label="關閉"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 內容區域 */}
        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <i className="fa-solid fa-spinner fa-spin text-2xl text-tertiary"></i>
              <span className="ml-3 text-tertiary">載入中...</span>
            </div>
          ) : fileMetadata ? (
            <div className="space-y-4">
              {/* 文件名 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">文件名</label>
                <div className="text-primary break-words">{fileMetadata.filename || fileName}</div>
              </div>

              {/* 檔案ID */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">檔案ID</label>
                <div className="text-primary font-mono text-sm break-all">{fileMetadata.file_id || fileId}</div>
              </div>

              {/* 文件大小 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">文件大小</label>
                <div className="text-primary">{formatFileSize(fileMetadata.file_size || 0)}</div>
              </div>

              {/* 上傳日期 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">上傳日期</label>
                <div className="text-primary">{formatDate(fileMetadata.upload_time || new Date().toISOString())}</div>
              </div>

              {/* 目前路徑 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">目前路徑</label>
                <div className="text-primary">{getCurrentPath()}</div>
              </div>

              {/* 文件類型 */}
              {fileMetadata.file_type && (
                <div>
                  <label className="text-sm font-medium text-tertiary block mb-1">文件類型</label>
                  <div className="text-primary">{fileMetadata.file_type}</div>
                </div>
              )}

              {/* 向量資料狀態 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">向量資料</label>
                <div className="flex items-center gap-2">
                  {hasVectors === true ? (
                    <>
                      <i className="fa-solid fa-check-circle text-green-500"></i>
                      <span className="text-green-500">已產生</span>
                    </>
                  ) : hasVectors === false ? (
                    <>
                      <i className="fa-solid fa-times-circle text-red-500"></i>
                      <span className="text-red-500">未產生</span>
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-question-circle text-tertiary"></i>
                      <span className="text-tertiary">未知</span>
                    </>
                  )}
                </div>
              </div>

              {/* 圖譜資料狀態 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">圖譜資料</label>
                <div className="flex items-center gap-2">
                  {hasGraph === true ? (
                    <>
                      <i className="fa-solid fa-check-circle text-green-500"></i>
                      <span className="text-green-500">已產生</span>
                    </>
                  ) : hasGraph === false ? (
                    <>
                      <i className="fa-solid fa-times-circle text-red-500"></i>
                      <span className="text-red-500">未產生</span>
                    </>
                  ) : (
                    <>
                      <i className="fa-solid fa-question-circle text-tertiary"></i>
                      <span className="text-tertiary">未知</span>
                    </>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-tertiary">
              <i className="fa-solid fa-exclamation-circle text-2xl mb-2"></i>
              <p>無法載入文件信息</p>
            </div>
          )}
        </div>

        {/* 底部按鈕 */}
        <div className="flex justify-end gap-2 p-4 border-t border-primary">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
          >
            關閉
          </button>
        </div>
      </div>
    </div>
  );
}
