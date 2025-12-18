// 代碼功能說明: 文件移動目錄選擇彈窗組件
// 創建日期: 2025-12-08 09:29:49 UTC+8
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-13 18:28:38 (UTC+8)

/**
 * 文件移動目錄選擇彈窗
 * 顯示目錄架構，讓用戶選擇要移動到的目標目錄
 */

import { useState, useEffect, useRef } from 'react';
import { X, Folder, FolderOpen, ChevronRight, ChevronDown } from 'lucide-react';
import { FileTreeResponse } from '../lib/api';

interface FileMoveModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (targetTaskId: string, targetFolderId: string | null) => void;
  fileId: string;
  fileName: string;
  treeData: FileTreeResponse | null;
  currentTaskId?: string | null; // 當前文件所在的 taskId
}

interface TreeNode {
  taskId: string;
  taskName: string;
  fileCount: number;
  isExpanded: boolean;
  level: number; // 縮進級別
}

const TEMP_WORKSPACE_ID = 'temp-workspace';
const TEMP_WORKSPACE_NAME = '任務工作區';

export default function FileMoveModal({
  isOpen,
  onClose,
  onConfirm,
  fileId: _fileId,
  fileName,
  treeData,
  currentTaskId,
}: FileMoveModalProps) {
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());
  const modalRef = useRef<HTMLDivElement>(null);

  // 修改時間：2025-12-09 - 動態獲取任務工作區 key，而不是使用 TEMP_WORKSPACE_ID
  const getWorkspaceKey = (): string | null => {
    if (!treeData || !treeData.data) {
      return null;
    }
    const { folders } = treeData.data;
    const foldersInfo = folders || {};
    for (const [key, folderInfo] of Object.entries(foldersInfo)) {
      if (folderInfo.folder_type === 'workspace') {
        return key;
      }
    }
    // 如果找不到，嘗試從 tree 的 key 中找
    if (treeData.data.tree) {
      for (const key of Object.keys(treeData.data.tree)) {
        if (key.endsWith('_workspace')) {
          return key;
        }
      }
    }
    return null;
  };

  // 當彈窗打開時，重置選中狀態並展開任務工作區
  useEffect(() => {
    if (isOpen) {
      setSelectedTaskId(null);
      const workspaceKey = getWorkspaceKey();
      if (workspaceKey) {
        setExpandedTasks(new Set([workspaceKey]));
      } else {
        setExpandedTasks(new Set([TEMP_WORKSPACE_ID])); // 兼容舊格式
      }
    }
  }, [isOpen]); // 移除 treeData 依賴，避免無限循環

  // 點擊外部關閉彈窗
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [isOpen, onClose]);

  // ESC 鍵關閉彈窗
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      return () => {
        window.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [isOpen, onClose]);

  // 構建目錄樹結構
  // 修改時間：2025-12-09 - 修復文件樹顯示邏輯，只顯示任務工作區及其子資料夾，不顯示排程任務
  const buildTreeNodes = (): TreeNode[] => {
    if (!treeData || !treeData.data) {
      return [];
    }

    const { tree, folders } = treeData.data;
    const foldersInfo = folders || {};
    const nodes: TreeNode[] = [];

    // 修改時間：2025-12-09 - 找到當前任務的任務工作區 key（格式：{task_id}_workspace）
    // 從 tree 或 folders 中找到任務工作區的 key
    let workspaceKey: string | null = null;
    for (const [key, folderInfo] of Object.entries(foldersInfo)) {
      if (folderInfo.folder_type === 'workspace') {
        workspaceKey = key;
        break;
      }
    }

    // 如果找不到，嘗試從 tree 的 key 中找（格式：{task_id}_workspace）
    if (!workspaceKey && tree) {
      for (const key of Object.keys(tree)) {
        if (key.endsWith('_workspace')) {
          workspaceKey = key;
          break;
        }
      }
    }

    if (!workspaceKey) {
      // 如果找不到任務工作區，返回空列表
      return [];
    }

    // 獲取子資料夾列表（遞歸查找）
    const getSubFolders = (parentId: string, level: number): TreeNode[] => {
      const subFolders: TreeNode[] = [];
      Object.entries(foldersInfo).forEach(([folderTaskId, folderInfo]) => {
        const folderParentId = folderInfo.parent_task_id;
        // 匹配父資料夾 ID
        if (folderParentId === parentId) {
          // 排除排程任務資料夾（folder_type === 'scheduled'）
          if (folderInfo.folder_type !== 'scheduled') {
            subFolders.push({
              taskId: folderTaskId,
              taskName: folderInfo.folder_name,
              fileCount: tree[folderTaskId]?.length || 0,
              isExpanded: expandedTasks.has(folderTaskId),
              level,
            });
          }
        }
      });
      return subFolders;
    };

    // 遞歸構建樹節點
    const buildNodes = (parentId: string, level: number): TreeNode[] => {
      const result: TreeNode[] = [];
      const subFolders = getSubFolders(parentId, level);

      subFolders.forEach((folder) => {
        result.push(folder);
        // 遞歸添加子資料夾
        const children = buildNodes(folder.taskId, level + 1);
        result.push(...children);
      });

      return result;
    };

    // 修改時間：2025-12-09 - 只顯示任務工作區（不顯示排程任務）
    // 添加任務工作區節點（level 0）
    const workspaceInfo = foldersInfo[workspaceKey];
    if (workspaceInfo) {
      nodes.push({
        taskId: workspaceKey,
        taskName: workspaceInfo.folder_name || TEMP_WORKSPACE_NAME,
        fileCount: tree[workspaceKey]?.length || 0,
        isExpanded: expandedTasks.has(workspaceKey),
        level: 0,
      });

      // 添加任務工作區下的子資料夾（level 1）
      const workspaceChildren = buildNodes(workspaceKey, 1);
      nodes.push(...workspaceChildren);
    }

    return nodes;
  };

  const treeNodes = buildTreeNodes();

  // 修改時間：2025-12-08 09:43:52 UTC+8 - 構建選中目錄的完整路徑
  // 構建選中目錄的完整路徑
  const getSelectedPath = (): string => {
    if (!selectedTaskId || !treeData?.data?.folders) {
      return '';
    }

    const foldersInfo = treeData.data.folders;
    const pathParts: string[] = [];

    // 修改時間：2025-12-09 - 修復路徑構建邏輯，正確處理任務工作區
    // 遞歸查找父目錄
    const buildPath = (taskId: string): void => {
      // 檢查是否為任務工作區（格式：{task_id}_workspace）
      if (taskId.endsWith('_workspace')) {
        const folderInfo = foldersInfo[taskId];
        if (folderInfo) {
          pathParts.unshift(folderInfo.folder_name || TEMP_WORKSPACE_NAME);
        } else {
          pathParts.unshift(TEMP_WORKSPACE_NAME);
        }
        return;
      }

      // 檢查是否為 temp-workspace（舊格式兼容）
      if (taskId === TEMP_WORKSPACE_ID) {
        pathParts.unshift(TEMP_WORKSPACE_NAME);
        return;
      }

      const folderInfo = foldersInfo[taskId];
      if (folderInfo) {
        pathParts.unshift(folderInfo.folder_name);

        // 如果有父目錄，繼續遞歸
        if (folderInfo.parent_task_id) {
          buildPath(folderInfo.parent_task_id);
        } else {
          // 如果父目錄是 null，表示是頂級目錄，前面加上任務工作區
          pathParts.unshift(TEMP_WORKSPACE_NAME);
        }
      } else {
        // 如果找不到資料夾信息，可能是任務工作區或其他特殊目錄
        if (taskId.endsWith('_workspace') || taskId === TEMP_WORKSPACE_ID) {
          pathParts.unshift(TEMP_WORKSPACE_NAME);
        } else {
          pathParts.unshift(taskId);
        }
      }
    };

    buildPath(selectedTaskId);
    return pathParts.join(' / ');
  };

  const selectedPath = getSelectedPath();

  // 取得 API 需要的目標任務 ID（去除 _workspace 或使用資料夾的 task_id）
  const getTargetTaskId = (taskId: string | null): string | null => {
    if (!taskId || !treeData?.data?.folders) {
      return taskId;
    }

    // 如果是任務工作區，去掉後綴 _workspace 即為實際任務 ID
    if (taskId.endsWith('_workspace')) {
      return taskId.replace('_workspace', '');
    }

    // 如果是資料夾，取該資料夾的 task_id（資料夾所屬的任務）
    const folderInfo = treeData.data.folders[taskId];
    if (folderInfo?.task_id) {
      return folderInfo.task_id;
    }

    // 其他情況（兼容舊格式），直接返回
    return taskId;
  };

  // 切換展開/折疊
  const toggleExpand = (taskId: string) => {
    setExpandedTasks((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      return newSet;
    });
  };

  // 處理確認移動
  const handleConfirm = () => {
    if (selectedTaskId) {
      const targetTaskId = getTargetTaskId(selectedTaskId);
      console.log('[FileMoveModal] Confirm move', {
        selectedTaskId,
        targetTaskId,
        folderInfo: treeData?.data?.folders?.[selectedTaskId] || null,
      });
      onConfirm(targetTaskId || '', selectedTaskId);
      onClose();
    }
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        ref={modalRef}
        className="bg-primary border border-border rounded-lg shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col"
      >
        {/* 標題欄 */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-primary">移動文件</h2>
          <button
            onClick={onClose}
            className="text-tertiary hover:text-primary transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 文件信息 */}
        <div className="p-4 border-b border-border">
          <p className="text-sm text-secondary">
            選擇目標目錄來移動文件：
            <span className="font-medium text-primary ml-1">{fileName}</span>
          </p>
        </div>

        {/* 目錄樹 */}
        <div className="flex-1 overflow-y-auto p-4">
          {treeNodes.length === 0 ? (
            <div className="text-center text-tertiary py-8">
              暫無可用目錄
            </div>
          ) : (
            <div className="space-y-1">
              {treeNodes.map((node) => {
                const isSelected = selectedTaskId === node.taskId;
                const isExpanded = expandedTasks.has(node.taskId);
                // 修改時間：2025-12-08 10:37:00 UTC+8 - 修復子節點判斷邏輯
                // 檢查是否有子節點：查找 level 比當前節點大 1 且在當前節點之後的節點
                const currentIndex = treeNodes.indexOf(node);
                const hasChildren = treeNodes.slice(currentIndex + 1).some(
                  (n) => n.level === node.level + 1
                );
                const indent = node.level * 20;

                // 修改時間：2025-12-08 10:37:00 UTC+8 - 只顯示展開節點的子節點
                // 如果當前節點的父節點是折疊的，不顯示
                let shouldDisplay = true;
                if (node.level > 0) {
                  // 查找父節點
                  for (let i = currentIndex - 1; i >= 0; i--) {
                    const prevNode = treeNodes[i];
                    if (prevNode.level === node.level - 1) {
                      // 找到父節點，檢查是否展開
                      if (!expandedTasks.has(prevNode.taskId)) {
                        shouldDisplay = false;
                      }
                      break;
                    }
                  }
                }

                if (!shouldDisplay) {
                  return null;
                }

                return (
                  <div
                    key={node.taskId}
                    className={`flex items-center py-2 px-3 rounded cursor-pointer transition-colors ${
                      isSelected
                        ? 'bg-blue-500/20 border border-blue-500/50'
                        : 'hover:bg-secondary/50'
                    } ${node.taskId === currentTaskId ? 'opacity-50 cursor-not-allowed' : ''}`}
                    style={{ paddingLeft: `${indent + 12}px` }}
                    onClick={() => {
                      // 如果當前文件就在這個目錄，不允許選擇
                      if (node.taskId === currentTaskId) {
                        return;
                      }
                      setSelectedTaskId(node.taskId);
                    }}
                  >
                    {/* 展開/折疊按鈕 */}
                    {hasChildren ? (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleExpand(node.taskId);
                        }}
                        className="mr-2 text-tertiary hover:text-primary"
                      >
                        {isExpanded ? (
                          <ChevronDown className="w-4 h-4" />
                        ) : (
                          <ChevronRight className="w-4 h-4" />
                        )}
                      </button>
                    ) : (
                      <div className="w-6 mr-2" />
                    )}

                    {/* 資料夾圖標 */}
                    {isExpanded ? (
                      <FolderOpen className="w-4 h-4 mr-2 text-blue-400" />
                    ) : (
                      <Folder className="w-4 h-4 mr-2 text-blue-400" />
                    )}

                    {/* 資料夾名稱 */}
                    <span className="flex-1 text-sm text-primary">
                      {node.taskName}
                    </span>

                    {/* 文件數量 */}
                    <span className="text-xs text-tertiary ml-2">
                      ({node.fileCount})
                    </span>

                    {/* 當前目錄標記 */}
                    {node.taskId === currentTaskId && (
                      <span className="text-xs text-yellow-400 ml-2">(當前目錄)</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 操作按鈕 */}
        <div className="flex items-center justify-between gap-3 p-4 border-t border-border">
          {/* 修改時間：2025-12-08 09:43:52 UTC+8 - 在按鈕區左側顯示選中目錄的路徑 */}
          <div className="flex-1 min-w-0">
            {selectedTaskId && selectedPath ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-tertiary">目標路徑：</span>
                <span className="text-sm text-primary font-medium truncate" title={selectedPath}>
                  {selectedPath}
                </span>
              </div>
            ) : (
              <div className="text-xs text-tertiary">請選擇目標目錄</div>
            )}
          </div>
          <div className="flex items-center gap-3 flex-shrink-0">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-secondary hover:text-primary transition-colors"
            >
              取消
            </button>
            <button
              onClick={handleConfirm}
              disabled={!selectedTaskId || selectedTaskId === currentTaskId}
              className="px-4 py-2 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              確認移動
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
