/**
 * 代碼功能說明: 文件樹組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-14 14:20:04 (UTC+8)
 *
 * 功能說明:
 * - 顯示按 task_id 組織的文件目錄結構
 * - 支持展開/折疊目錄
 * - 點擊目錄可以篩選文件列表
 * - 顯示"任務工作區"作為特殊目錄
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Folder, FolderOpen, File as FileIcon, ChevronRight, ChevronDown, X } from 'lucide-react';
import { getFileTree, FileTreeResponse, getFileList, deleteFile, renameFile, copyFile, moveFile, renameFolder, createFolder, deleteFolder, moveFolder, getFileVectors, getFileGraph, FileMetadata } from '../lib/api';
import { FileNode } from './Sidebar';
import { getMockFiles, hasMockFiles, getMockFile } from '../lib/mockFileStorage';
// 修改時間：2025-12-08 08:46:00 UTC+8 - 添加 clearFileTreeCache 導入，用於登錄時清除緩存
import { useClipboardState, useBatchSelection, saveClipboardState, loadClipboardState, clearClipboardState, ClipboardItem, clearFileTreeCache } from '../lib/fileOperationState';
// 修改時間：2025-12-08 09:29:49 UTC+8 - 添加文件移動目錄選擇彈窗組件
import FileMoveModal from './FileMoveModal';
// 修改時間：2025-12-09 - 添加文件數據預覽組件
import FileDataPreview from './FileDataPreview';
// 修改時間：2025-12-14 12:58:00 (UTC+8) - 新建檔案（只輸入檔名，建立空白 .md）
import NewFileOrUploadModal from './NewFileOrUploadModal';

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
const EXPANDED_TASKS_STORAGE_KEY = 'fileTree_expandedTasks';
const DRAFT_FILES_STORAGE_KEY = 'ai-box-draft-files-v1';

function isDraftFileId(fileId: string): boolean {
  return typeof fileId === 'string' && fileId.startsWith('draft-');
}

function loadDraftFilesFromStorage(): Record<string, FileMetadata[]> {
  try {
    const raw = localStorage.getItem(DRAFT_FILES_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return {};
    return parsed as Record<string, FileMetadata[]>;
  } catch {
    return {};
  }
}

function saveDraftFilesToStorage(drafts: Record<string, FileMetadata[]>): void {
  try {
    localStorage.setItem(DRAFT_FILES_STORAGE_KEY, JSON.stringify(drafts));
  } catch {
    // ignore
  }
}

function cloneFileNodes(nodes: FileNode[]): FileNode[] {
  return nodes.map((n) => ({
    id: n.id,
    name: n.name,
    type: n.type,
    children: n.children ? cloneFileNodes(n.children) : undefined,
  }));
}

function tryInsertFileIntoFolder(nodes: FileNode[], folderId: string, fileNode: FileNode): boolean {
  for (const n of nodes) {
    if (n.type !== 'folder') continue;
    if (n.id === folderId) {
      if (!n.children) n.children = [];
      if (!n.children.some((c) => c.type === 'file' && c.id === fileNode.id)) {
        n.children.push(fileNode);
      }
      return true;
    }
    if (n.children && n.children.length > 0) {
      const ok = tryInsertFileIntoFolder(n.children, folderId, fileNode);
      if (ok) return true;
    }
  }
  return false;
}

function mergeDraftsIntoFileTree(
  fileTree: FileNode[] | undefined,
  draftsByContainerKey: Record<string, FileMetadata[]>,
): FileNode[] | undefined {
  if (!fileTree || fileTree.length === 0) return fileTree;
  const next = cloneFileNodes(fileTree);

  const seen = new Set<string>();
  const visit = (nodes: FileNode[]) => {
    nodes.forEach((n) => {
      seen.add(n.id);
      if (n.children) visit(n.children);
    });
  };
  visit(next);

  for (const [containerKey, drafts] of Object.entries(draftsByContainerKey || {})) {
    const list = Array.isArray(drafts) ? drafts : [];
    for (const d of list) {
      const fid = String((d as any)?.file_id || '').trim();
      const name = String((d as any)?.filename || '').trim();
      if (!fid || !name) continue;
      if (seen.has(fid)) continue;

      const node: FileNode = { id: fid, name, type: 'file' };
      const candidates: string[] = [];
      if (containerKey) candidates.push(containerKey);
      if (containerKey.endsWith('_workspace')) candidates.push(containerKey.replace('_workspace', ''));
      if (containerKey.endsWith('_scheduled')) candidates.push(containerKey.replace('_scheduled', ''));

      let inserted = false;
      for (const key of candidates) {
        if (key && tryInsertFileIntoFolder(next, key, node)) {
          inserted = true;
          break;
        }
      }
      if (!inserted) {
        next.push(node);
      }
      seen.add(fid);
    }
  }
  return next;
}

// 修改時間：2025-12-08 10:32:00 UTC+8 - 從 localStorage 加載展開狀態
const loadExpandedTasksFromStorage = (): Set<string> => {
  try {
    const stored = localStorage.getItem(EXPANDED_TASKS_STORAGE_KEY);
    if (stored) {
      const array = JSON.parse(stored);
      return new Set(array);
    }
  } catch (error) {
    console.error('[FileTree] Failed to load expanded tasks from storage:', error);
  }
  // 默認展開任務工作區
  return new Set([TEMP_WORKSPACE_ID]);
};

// 修改時間：2025-12-08 10:32:00 UTC+8 - 保存展開狀態到 localStorage
const saveExpandedTasksToStorage = (expandedTasks: Set<string>) => {
  try {
    const array = Array.from(expandedTasks);
    localStorage.setItem(EXPANDED_TASKS_STORAGE_KEY, JSON.stringify(array));
  } catch (error) {
    console.error('[FileTree] Failed to save expanded tasks to storage:', error);
  }
};

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
  // 修改時間：2025-12-08 10:32:00 UTC+8 - 從 localStorage 加載展開狀態
  const [expandedTasks, setExpandedTasks] = useState<Set<string>>(loadExpandedTasksFromStorage());
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; fileId: string; fileName: string } | null>(null);
  const [folderContextMenu, setFolderContextMenu] = useState<{ x: number; y: number; taskId: string; taskName: string } | null>(null);
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null); // 選中的文件ID
  const [showFileInfoModal, setShowFileInfoModal] = useState(false);
  const [fileInfo, setFileInfo] = useState<{ fileId: string; fileName: string } | null>(null);
  const [notification, setNotification] = useState<{ message: string; type: 'success' | 'error' | 'warning' } | null>(null);
  const [focusedFolderId, setFocusedFolderId] = useState<string | null>(null); // 當前聚焦的資料夾ID
  // 修改時間：2025-12-14 13:28:13 (UTC+8) - 新增檔案改為「本地草稿」，Apply 後才寫入後端
  const [draftFilesByContainerKey, setDraftFilesByContainerKey] = useState<Record<string, FileMetadata[]>>(
    loadDraftFilesFromStorage()
  );
  const mergedFileTreeForRender = useMemo(
    () => mergeDraftsIntoFileTree(fileTree, draftFilesByContainerKey),
    [fileTree, draftFilesByContainerKey]
  );

  // 修改時間：2025-12-14 14:10:04 (UTC+8) - 移除 openDraftInDocAssistant（草稿檔直接通過 onFileSelect 預覽）
  // 如果需要跳轉到文件助手，可以在 DocumentAssistant 中處理

  // 監聽本地草稿建立事件（不打後端）
  useEffect(() => {
    const handler = (event: CustomEvent) => {
      const detail: any = event?.detail || {};
      const containerKey = String(detail?.containerKey || '').trim();
      const taskId = String(detail?.taskId || '').trim();
      const filename = String(detail?.filename || '').trim();
      const draftId = String(detail?.draftId || '').trim();
      if (!containerKey || !taskId || !filename || !draftId) return;

      console.log('[FileTree] localDraftFileCreated', { containerKey, taskId, filename, draftId });

      const newDraft: FileMetadata = {
        file_id: draftId,
        filename: filename,
        file_type: 'text/markdown',
        file_size: 0,
        user_id: '',
        task_id: taskId,
        tags: ['draft'],
        upload_time: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      } as any;

      setDraftFilesByContainerKey((prev) => {
        const current = Array.isArray(prev[containerKey]) ? prev[containerKey] : [];
        // 避免重複
        if (current.some((f) => f?.file_id === draftId)) return prev;
        const next = {
          ...prev,
          [containerKey]: [...current, newDraft],
        };
        saveDraftFilesToStorage(next);
        return next;
      });
    };

    window.addEventListener('localDraftFileCreated', handler as EventListener);
    return () => window.removeEventListener('localDraftFileCreated', handler as EventListener);
  }, []);

  const removeDraftById = useCallback((draftId: string) => {
    setDraftFilesByContainerKey((prev) => {
      let changed = false;
      const next: Record<string, FileMetadata[]> = {};
      for (const [k, arr] of Object.entries(prev || {})) {
        const list = Array.isArray(arr) ? arr : [];
        const filtered = list.filter((f: any) => f?.file_id !== draftId);
        if (filtered.length !== list.length) changed = true;
        if (filtered.length > 0) next[k] = filtered;
      }
      if (changed) {
        saveDraftFilesToStorage(next);
        return next;
      }
      return prev;
    });
  }, []);
  const [showRenameModal, setShowRenameModal] = useState(false); // 顯示重命名對話框
  const [renameTarget, setRenameTarget] = useState<{ id: string; name: string; type: 'folder' | 'file' } | null>(null); // 重命名目標
  const [renameInput, setRenameInput] = useState(''); // 重命名輸入值
  const [showNewFolderModal, setShowNewFolderModal] = useState(false); // 顯示新增資料夾對話框
  const [newFolderParentId, setNewFolderParentId] = useState<string | null>(null); // 新增資料夾的父資料夾ID
  const [newFolderInput, setNewFolderInput] = useState(''); // 新增資料夾輸入值
  const [showDeleteFolderModal, setShowDeleteFolderModal] = useState(false); // 顯示刪除資料夾確認對話框
  const [deleteFolderTarget, setDeleteFolderTarget] = useState<{ taskId: string; taskName: string } | null>(null); // 要刪除的資料夾
  const [showMoveModal, setShowMoveModal] = useState(false); // 顯示移動目錄彈窗
  const [moveFileTarget, setMoveFileTarget] = useState<{ fileId: string; fileName: string; currentTaskId: string | null; isDraft?: boolean } | null>(null); // 要移動的文件
  const [showDeleteFileModal, setShowDeleteFileModal] = useState(false); // 顯示刪除文件確認對話框
  const [deleteFileTarget, setDeleteFileTarget] = useState<{ fileId: string; fileName: string } | null>(null); // 要刪除的文件
  const [showReuploadModal, setShowReuploadModal] = useState(false); // 顯示重新上傳文件確認對話框
  const [reuploadFileTarget, setReuploadFileTarget] = useState<{ fileId: string; fileName: string; taskId: string | null } | null>(null); // 要重新上傳的文件
  // 修改時間：2025-12-09 - 添加文件數據預覽狀態
  const [showDataPreview, setShowDataPreview] = useState(false); // 顯示數據預覽對話框
  const [previewFile, setPreviewFile] = useState<FileMetadata | null>(null); // 預覽的文件
  const [previewMode, setPreviewMode] = useState<'text' | 'vector' | 'graph'>('text'); // 預覽模式
  // 修改時間：2025-12-14 12:58:00 (UTC+8) - 新建檔案 Modal（只輸入檔名）
  const [showNewFileModal, setShowNewFileModal] = useState(false);
  const [newFileTarget, setNewFileTarget] = useState<{
    taskId: string | null;
    folderId: string | null;
    folderLabel: string | null;
    containerKey: string | null;
  } | null>(null);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const folderContextMenuRef = useRef<HTMLDivElement>(null);
  const fileTreeRef = useRef<HTMLDivElement>(null);
  const renameInputRef = useRef<HTMLInputElement>(null);
  // 修改時間：2025-01-27 - 使用 useRef 存儲最新的 fileTree prop，確保事件監聽器始終使用最新值
  const fileTreeRef_current = useRef<FileNode[] | undefined>(fileTree);
  const newFolderInputRef = useRef<HTMLInputElement>(null);
  const folderRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // 使用剪貼板和批量選擇功能
  const { setClipboard, cutItems } = useClipboardState();
  const batchSelection = useBatchSelection();
  const [latestTreeData, setLatestTreeData] = useState<FileTreeResponse | null>(null);
  const [isReloadingTree, setIsReloadingTree] = useState(false);
  const [suppressPropFallback, setSuppressPropFallback] = useState(false); // 移動/重載期間避免回退到舊 fileTree

  // 修改時間：2025-12-09 - 將 FileTreeResponse 轉換為 FileNode[]（用於更新父組件的 fileTree prop）
  const convertTreeDataToFileTree = useCallback(
    (treeData: FileTreeResponse): FileNode[] => {
      if (!treeData.data) {
        return [];
      }

      const { tree, folders } = treeData.data;
      const folderMap = new Map<string, FileNode>();
      const processedFolders = new Set<string>();

      console.log('[FileTree] Converting treeData to fileTree', {
        treeKeys: Object.keys(tree || {}),
        foldersKeys: Object.keys(folders || {}),
        treeStructure: Object.entries(tree || {}).map(([k, v]) => ({ key: k, fileCount: (v as any[]).length })),
      });

      // 先創建所有資料夾節點
      Object.entries(folders || {}).forEach(([folderId, folderInfo]) => {
        folderMap.set(folderId, {
          id: folderId,
          name: folderInfo.folder_name || folderId,
          type: 'folder',
          children: [],
        });
      });

      // 建立資料夾的父子關係
      Object.entries(folders || {}).forEach(([folderId, folderInfo]) => {
        const folderNode = folderMap.get(folderId);
        if (!folderNode) return;

        const parentId = folderInfo.parent_task_id;
        if (parentId) {
          if (folderMap.has(parentId)) {
            const parentNode = folderMap.get(parentId);
            if (parentNode && parentNode.type === 'folder') {
              parentNode.children = parentNode.children || [];
              parentNode.children.push(folderNode);
              processedFolders.add(folderId);
              console.log('[FileTree] Added child folder to parent', {
                childId: folderId,
                childName: folderNode.name,
                parentId: parentId,
                parentName: parentNode.name,
              });
            }
          } else {
            console.warn('[FileTree] Parent folder not found in folderMap', {
              folderId,
              folderName: folderNode.name,
              parentId,
            });
          }
        }
      });

      // 將文件添加到對應的資料夾（根據 tree 中的 key，即 folder_id）
      Object.entries(tree || {}).forEach(([folderId, files]) => {
        const folderNode = folderMap.get(folderId);
        if (folderNode && folderNode.type === 'folder') {
          folderNode.children = folderNode.children || [];
          const fileCount = (files as any[]).length;
          (files as any[]).forEach((file: any) => {
            folderNode.children!.push({
              id: file.file_id || file.id,
              name: file.filename || file.name,
              type: 'file',
            });
          });
          console.log('[FileTree] Added files to folder', {
            folderId,
            folderName: folderNode.name,
            fileCount,
            fileIds: (files as any[]).map(f => f.file_id || f.id),
            totalChildrenCount: folderNode.children.length,
          });
        } else if (!folderMap.has(folderId)) {
          // 如果資料夾不存在，可能是 workspace 或其他特殊節點，記錄警告
          console.warn('[FileTree] Folder not found in folders map, files will be lost', {
            folderId,
            fileCount: (files as any[]).length
          });
        } else {
          console.warn('[FileTree] Folder node exists but is not a folder type', {
            folderId,
            nodeType: folderNode?.type,
          });
        }
      });

      // 返回根節點（parent_task_id 為 null 或不在 folders 中的節點）
      const rootNodes: FileNode[] = [];
      Object.entries(folders || {}).forEach(([folderId, folderInfo]) => {
        const isProcessed = processedFolders.has(folderId);
        const hasParent = folderInfo.parent_task_id && folderMap.has(folderInfo.parent_task_id);
        const shouldBeRoot = !isProcessed && (!folderInfo.parent_task_id || !folderMap.has(folderInfo.parent_task_id));

        if (shouldBeRoot) {
          const node = folderMap.get(folderId);
          if (node) {
            rootNodes.push(node);
            console.log('[FileTree] Added root node', {
              folderId,
              folderName: node.name,
              isProcessed,
              hasParent,
              childrenCount: node.children?.length || 0,
            });
          }
        } else {
          console.log('[FileTree] Skipped non-root node', {
            folderId,
            folderName: folderMap.get(folderId)?.name,
            isProcessed,
            hasParent,
            parentId: folderInfo.parent_task_id,
          });
        }
      });

      console.log('[FileTree] Converted fileTree', {
        rootNodesCount: rootNodes.length,
        rootNodeIds: rootNodes.map(n => n.id),
        rootNodesWithChildren: rootNodes.map(n => ({
          id: n.id,
          name: n.name,
          childrenCount: n.children?.length || 0,
          childrenIds: n.children?.map(c => c.id) || [],
        })),
      });

      return rootNodes;
    },
    []
  );

  // 修改時間：2025-12-09 - 當使用 fileTree prop 時，為移動彈窗構建兼容的 treeData 結構
  const buildTreeDataFromFileTree = useCallback(
    (nodes: FileNode[]): FileTreeResponse => {
      const tree: Record<string, any[]> = {};
      const folders: Record<
        string,
        {
          folder_name: string;
          parent_task_id?: string | null;
          user_id: string;
          folder_type?: string;
          task_id?: string;
        }
      > = {};

      const effectiveUserId =
        userId || localStorage.getItem('user_id') || localStorage.getItem('userEmail') || '';

      const traverse = (node: FileNode, parentId: string | null, currentTaskId: string | null) => {
        // 嘗試從節點 ID 推斷任務 ID（如果是任務工作區，格式為 {taskId}_workspace）
        let nextTaskId = currentTaskId;
        if (node.type === 'folder' && node.id.endsWith('_workspace')) {
          nextTaskId = node.id.replace('_workspace', '');
        }

        if (node.type === 'folder') {
          folders[node.id] = {
            folder_name: node.name,
            parent_task_id: parentId,
            user_id: effectiveUserId,
            task_id: nextTaskId || undefined,
            folder_type: node.id.endsWith('_workspace') ? 'workspace' : undefined,
          };
          if (!tree[node.id]) {
            tree[node.id] = [];
          }
          if (node.children && node.children.length > 0) {
            node.children.forEach((child) => traverse(child, node.id, nextTaskId));
          }
        } else {
          const key = parentId ?? TEMP_WORKSPACE_ID;
          if (!tree[key]) {
            tree[key] = [];
          }
          tree[key].push({
            file_id: node.id,
            filename: node.name,
          });
        }
      };

      nodes.forEach((n) => traverse(n, null, null));

      return {
        success: true,
        data: {
          tree,
          folders,
          total_tasks: Object.keys(tree).length,
          total_files: Object.values(tree).reduce((sum, arr) => sum + arr.length, 0),
        },
      };
    },
    [userId],
  );

  // 構建提供給移動彈窗使用的 treeData（優先使用 API treeData，若無則用 fileTree prop 構建）
  const modalTreeData: FileTreeResponse | null =
    treeData || (fileTree && fileTree.length > 0 ? buildTreeDataFromFileTree(fileTree) : null);

  // 處理重命名確認
  const handleRenameConfirm = useCallback(() => {
    if (!renameTarget || !renameInput.trim() || renameInput.trim() === renameTarget.name) {
      return;
    }

    // 修改時間：2025-12-14 14:10:04 (UTC+8) - 草稿檔支持更名（更新 localStorage）
    if (renameTarget.type === 'file' && isDraftFileId(renameTarget.id)) {
      const newFilename = renameInput.trim();
      // 確保檔名有副檔名（如果是 .md 檔）
      const finalFilename = newFilename.toLowerCase().endsWith('.md') ? newFilename : `${newFilename}.md`;

      // 更新 localStorage 中的草稿檔名
      setDraftFilesByContainerKey((prev) => {
        const next: Record<string, FileMetadata[]> = {};
        let changed = false;
        for (const [containerKey, drafts] of Object.entries(prev || {})) {
          const list = Array.isArray(drafts) ? drafts : [];
          const updated = list.map((d: any) => {
            if (d?.file_id === renameTarget.id) {
              changed = true;
              return { ...d, filename: finalFilename };
            }
            return d;
          });
          if (updated.length > 0) next[containerKey] = updated;
        }
        if (changed) {
          saveDraftFilesToStorage(next);
          setNotification({ message: '草稿檔更名成功', type: 'success' });
          setTimeout(() => setNotification(null), 3000);
        }
        return changed ? next : prev;
      });

      setShowRenameModal(false);
      setRenameTarget(null);
      setRenameInput('');
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

    // 如果 newFolderParentId 是 null，传递 null 给后端（在根节点创建）
    // 如果 newFolderParentId 是 undefined，传递 undefined（使用默认值）
    // 如果 newFolderParentId 有值，传递该值（在指定文件夹下创建）
    const parentIdToSend = newFolderParentId === null ? null : (newFolderParentId || undefined);
    createFolder(newFolderInput.trim(), parentIdToSend)
      .then((result) => {
        if (result.success) {
          console.log('[FileTree] Folder created successfully', {
            folderName: newFolderInput.trim(),
            parentId: parentIdToSend,
            result: result.data
          });
          setNotification({ message: '資料夾創建成功', type: 'success' });
          setTimeout(() => setNotification(null), 3000);

          // 修改時間：2025-01-27 - 如果使用 fileTree prop，需要觸發事件通知父組件更新
          // 觸發文件樹更新事件，讓 Home 組件重新加載文件樹
          window.dispatchEvent(new CustomEvent('fileTreeUpdated', {
            detail: {
              taskId: taskId,
              folderCreated: true,
              folderName: newFolderInput.trim(),
              parentId: parentIdToSend
            }
          }));

          // 如果使用 fileTree prop，並且有 onFileTreeChange 回調，嘗試從 API 重新加載
          if (fileTree && fileTree.length > 0 && onFileTreeChange) {
            console.log('[FileTree] Using fileTree prop, triggering reload via onFileTreeChange');
            // 觸發父組件重新加載文件樹
            // 這裡我們觸發事件，讓 Home 組件處理重新加載
          }
        } else {
          setNotification({ message: result.message || '資料夾創建失敗', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
        }
      })
      .catch((error) => {
        console.error('[FileTree] Folder creation failed:', error);
        setNotification({ message: error.message || '資料夾創建失敗', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
      });

    setShowNewFolderModal(false);
    setNewFolderParentId(null);
    setNewFolderInput('');
  }, [newFolderParentId, newFolderInput, taskId, fileTree, onFileTreeChange]);

  // 處理新增資料夾取消
  const handleNewFolderCancel = useCallback(() => {
    setShowNewFolderModal(false);
    setNewFolderParentId(null);
    setNewFolderInput('');
  }, []);

  // 修改時間：2025-12-08 10:32:00 UTC+8 - 展開指定的目錄（用於文件移動後）
  const expandTask = useCallback((taskId: string) => {
    setExpandedTasks((prev) => {
      if (prev.has(taskId)) {
        return prev; // 已經展開，不需要更新
      }
      const newSet = new Set(prev);
      newSet.add(taskId);
      // 保存到 localStorage
      saveExpandedTasksToStorage(newSet);
      return newSet;
    });
  }, []);

  // 修改時間：2025-12-14 14:10:04 (UTC+8) - 處理文件移動確認（支持草稿檔）
  const handleMoveConfirm = useCallback((targetTaskId: string | null, targetFolderId: string | null) => {
    if (!moveFileTarget) {
      return;
    }

    // 驗證 targetTaskId
    if (!targetTaskId || typeof targetTaskId !== 'string') {
      setNotification({ message: '請選擇有效的目標目錄', type: 'error' });
      setTimeout(() => setNotification(null), 3000);
      return;
    }

    // 修改時間：2025-12-14 14:10:04 (UTC+8) - 草稿檔移動：更新 localStorage
    const isDraft = (moveFileTarget as any).isDraft || isDraftFileId(moveFileTarget.fileId);
    if (isDraft) {
      const targetContainerKey = targetFolderId || `${targetTaskId}_workspace`;

      // 從舊的 containerKey 移除，添加到新的 containerKey
      setDraftFilesByContainerKey((prev) => {
        const next: Record<string, FileMetadata[]> = {};
        let found = false;
        let draftToMove: FileMetadata | null = null;

        // 找出要移動的草稿檔
        for (const [containerKey, drafts] of Object.entries(prev || {})) {
          const list = Array.isArray(drafts) ? drafts : [];
          const filtered = list.filter((d: any) => {
            if (d?.file_id === moveFileTarget.fileId) {
              found = true;
              draftToMove = { ...d, task_id: targetTaskId };
              return false; // 從舊位置移除
            }
            return true;
          });
          if (filtered.length > 0) next[containerKey] = filtered;
        }

        // 添加到新位置
        if (found && draftToMove) {
          if (!next[targetContainerKey]) {
            next[targetContainerKey] = [];
          }
          next[targetContainerKey].push(draftToMove);
          saveDraftFilesToStorage(next);
          setNotification({ message: '草稿檔已移動', type: 'success' });
          setTimeout(() => setNotification(null), 3000);
        }

        return found ? next : prev;
      });

      setShowMoveModal(false);
      setMoveFileTarget(null);
      return;
    }

    // 正式檔案：調用後端 API
    // 移動期間避免回退到舊的 fileTree prop
    setSuppressPropFallback(true);

    moveFile(moveFileTarget.fileId, targetTaskId, targetFolderId)
      .then((result) => {
        if (result.success) {
          setNotification({ message: '文件已移動', type: 'success' });
          setTimeout(() => setNotification(null), 3000);

          // 修改時間：2025-12-08 10:32:00 UTC+8 - 自動展開目標目錄
          // 如果移動到 temp-workspace，展開它
          if (targetTaskId === 'temp-workspace') {
            expandTask(TEMP_WORKSPACE_ID);
          } else {
            // 展開目標目錄
            expandTask(targetTaskId);
          }

          // 觸發文件樹更新：清除本地緩存並強制從後端重載
          try {
            if (userId) {
              clearFileTreeCache(userId, taskId);
            }
            // 如果有 fileTree prop，清空 ref 讓監聽器/後續渲染可以重載
            fileTreeRef_current.current = undefined;
            // 直接從 API 重新拉取最新樹
            if (taskId) {
              setIsReloadingTree(true);
              setLoading(true);
              setError(null);
              getFileTree({ user_id: userId, task_id: taskId })
                .then((response) => {
                  if (response.success && response.data) {
                    // 先本地更新樹，避免等待重載期間閃回舊工作區
                    if (treeData && treeData.data) {
                      const cloned = JSON.parse(JSON.stringify(treeData)) as FileTreeResponse;
                      const filesByFolder = cloned.data.tree || {};
                      const srcKeys = Object.keys(filesByFolder);
                      // 移除舊位置
                      srcKeys.forEach((k) => {
                        filesByFolder[k] = (filesByFolder[k] || []).filter((f: any) => f.file_id !== moveFileTarget.fileId);
                      });
                      // 添加到新資料夾
                      const targetKey = targetFolderId || `${targetTaskId}_workspace`;
                      if (!filesByFolder[targetKey]) {
                        filesByFolder[targetKey] = [];
                      }
                      const fileStub = filesByFolder[targetKey].find((f: any) => f.file_id === moveFileTarget.fileId);
                      if (!fileStub) {
                        filesByFolder[targetKey].push({
                          file_id: moveFileTarget.fileId,
                          filename: moveFileTarget.fileName,
                          file_type: '',
                          file_size: 0,
                          upload_time: '',
                          tags: [],
                        });
                      }
                      cloned.data.tree = filesByFolder;
                      setTreeData(cloned);
                      setLatestTreeData(cloned);
                    }
                    // 再寫入最新後端樹
                    setTreeData(response);
                    setLatestTreeData(response);

                    // 修改時間：2025-12-09 - 將新的 treeData 轉換為 FileNode[] 並更新父組件的 fileTree
                    // 這樣可以確保 fileTree prop 與 treeData 同步，避免渲染時使用舊的 fileTree
                    if (onFileTreeChange) {
                      try {
                        const newFileTree = convertTreeDataToFileTree(response);
                        console.log('[FileTree] Updating parent fileTree after move', {
                          newFileTreeLength: newFileTree.length,
                          newFileTreeIds: newFileTree.map(f => f.id),
                        });
                        onFileTreeChange(newFileTree);
                      } catch (e) {
                        console.error('[FileTree] Failed to convert treeData to fileTree', e);
                      }
                    }
                  } else {
                    setError('無法加載文件樹');
                  }
                })
                .catch((err: any) => {
                  console.error('[FileTree] Error reloading after move:', err);
                  setError(err.message || '加載文件樹失敗');
                })
                .finally(() => {
                  setLoading(false);
                  setIsReloadingTree(false);
              setSuppressPropFallback(false);
                });
            }
            // 廣播事件給其他監聽者
            window.dispatchEvent(new CustomEvent('fileTreeUpdated', { detail: { forceReload: true } }));
          } catch (e) {
            console.warn('[FileTree] failed to refresh after move', e);
          }
        } else {
          setNotification({ message: result.message || '移動文件失敗', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
        }
      })
      .catch((error) => {
        console.error('移動文件失敗:', error);
        setNotification({ message: error.message || '移動文件失敗', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
      });

    setShowMoveModal(false);
    setMoveFileTarget(null);
  }, [moveFileTarget, expandTask, convertTreeDataToFileTree, onFileTreeChange, taskId, userId]);

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

  // 修改時間：2025-12-08 13:30:00 UTC+8 - 處理刪除文件確認
  const handleDeleteFileConfirm = useCallback(async () => {
    if (!deleteFileTarget) {
      return;
    }

    // 修改時間：2025-12-14 13:28:13 (UTC+8) - 本地草稿刪除（不打後端）
    if (isDraftFileId(deleteFileTarget.fileId)) {
      removeDraftById(deleteFileTarget.fileId);
      setNotification({ message: '草稿已刪除（尚未提交後端）', type: 'success' });
      setTimeout(() => setNotification(null), 3000);
      if (selectedFileId === deleteFileTarget.fileId) {
        setSelectedFileId(null);
      }
      setShowDeleteFileModal(false);
      setDeleteFileTarget(null);
      return;
    }

    try {
      const result = await deleteFile(deleteFileTarget.fileId);
      if (result.success) {
        setNotification({ message: '文件刪除成功', type: 'success' });
        setTimeout(() => setNotification(null), 3000);

        // 觸發文件樹更新
        window.dispatchEvent(new CustomEvent('fileTreeUpdated'));

        // 如果刪除的是當前選中的文件，清除選中狀態
        if (selectedFileId === deleteFileTarget.fileId) {
          setSelectedFileId(null);
        }
      } else {
        setNotification({ message: result.message || '文件刪除失敗', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
      }
    } catch (error: any) {
      console.error('文件刪除失敗:', error);
      setNotification({ message: error.message || '文件刪除失敗', type: 'error' });
      setTimeout(() => setNotification(null), 3000);
    }

    setShowDeleteFileModal(false);
    setDeleteFileTarget(null);
  }, [deleteFileTarget, selectedFileId, removeDraftById]);

  // 處理刪除文件取消
  const handleDeleteFileCancel = useCallback(() => {
    setShowDeleteFileModal(false);
    setDeleteFileTarget(null);
  }, []);

  // 修改時間：2025-12-08 13:30:00 UTC+8 - 處理重新上傳文件確認
  const handleReuploadConfirm = useCallback(async () => {
    if (!reuploadFileTarget) {
      return;
    }

    try {
      // 1. 先刪除原文件的所有數據（ChromaDB、ArangoDB、文件存儲）
      const deleteResult = await deleteFile(reuploadFileTarget.fileId);
      if (!deleteResult.success) {
        setNotification({ message: '刪除原文件失敗，無法重新上傳', type: 'error' });
        setTimeout(() => setNotification(null), 3000);
        setShowReuploadModal(false);
        setReuploadFileTarget(null);
        return;
      }

      // 2. 觸發文件樹更新
      window.dispatchEvent(new CustomEvent('fileTreeUpdated'));

      // 3. 調用文件上傳功能（通過 onNewFile 回調）
      if (onNewFile) {
        // 使用原文件的 taskId 作為目標目錄，如果沒有則使用當前選中的 taskId 或 TEMP_WORKSPACE_ID（任務工作區）
        const targetTaskId = reuploadFileTarget.taskId || taskId || TEMP_WORKSPACE_ID;
        onNewFile(targetTaskId);
      }

      setNotification({ message: '原文件已刪除，請選擇新文件上傳', type: 'success' });
      setTimeout(() => setNotification(null), 3000);
    } catch (error: any) {
      console.error('重新上傳文件失敗:', error);
      setNotification({ message: error.message || '重新上傳文件失敗', type: 'error' });
      setTimeout(() => setNotification(null), 3000);
    }

    setShowReuploadModal(false);
    setReuploadFileTarget(null);
  }, [reuploadFileTarget, onNewFile, taskId]);

  // 處理重新上傳文件取消
  const handleReuploadCancel = useCallback(() => {
    setShowReuploadModal(false);
    setReuploadFileTarget(null);
  }, []);

  // 修改時間：2025-12-08 10:32:00 UTC+8 - 切換文件夾展開/折疊狀態，並保存到 localStorage
  const toggleTask = useCallback((taskId: string) => {
    setExpandedTasks((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(taskId)) {
        newSet.delete(taskId);
      } else {
        newSet.add(taskId);
      }
      // 保存到 localStorage
      saveExpandedTasksToStorage(newSet);
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
      const currentContextMenu = contextMenu;
      const currentFolderContextMenu = folderContextMenu;
      if (currentContextMenu || currentFolderContextMenu) return;

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
        // 修改時間：2025-12-08 09:32:31 UTC+8 - 修復類型錯誤，從 treeData 中查找文件名
        let fileName = selectedFileId;
        // 從 treeData 中查找文件名（不依賴 contextMenu，因為快捷鍵可能在任何時候觸發）
        if (treeData?.data?.tree) {
          for (const files of Object.values(treeData.data.tree)) {
            const file = files.find((f: any) => f.file_id === selectedFileId);
            if (file) {
              fileName = file.filename || selectedFileId;
              break;
            }
          }
        }
        const clipboardItems: ClipboardItem[] = [{
          id: selectedFileId,
          type: 'file',
          name: fileName,
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
        // 修改時間：2025-12-08 09:32:31 UTC+8 - 修復類型錯誤，從 treeData 中查找文件名
        let fileName = selectedFileId;
        // 從 treeData 中查找文件名（不依賴 contextMenu，因為快捷鍵可能在任何時候觸發）
        if (treeData?.data?.tree) {
          for (const files of Object.values(treeData.data.tree)) {
            const file = files.find((f: any) => f.file_id === selectedFileId);
            if (file) {
              fileName = file.filename || selectedFileId;
              break;
            }
          }
        }
        const clipboardItems: ClipboardItem[] = [{
          id: selectedFileId,
          type: 'file',
          name: fileName,
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

  // 修改時間：2025-12-14 13:22:37 (UTC+8) - 新增檔案：避免 folderKey 無法解析時誤建新 task
  const resolveTaskIdFromFolderKey = useCallback(
    (key: string | null): string | null => {
      if (!key) return selectedTaskId || null;
      const foldersInfo = treeData?.data?.folders || {};
      const info: any = (foldersInfo as any)[key];
      const direct = info?.task_id;
      if (typeof direct === 'string' && direct.trim()) {
        return direct.trim();
      }
      // 若無 treeData/folders mapping（例如使用 fileTree prop 分支），保守使用目前選取 task
      if ((!foldersInfo || Object.keys(foldersInfo as any).length === 0) && selectedTaskId) {
        return selectedTaskId;
      }
      if (key.endsWith('_workspace')) {
        return key.replace('_workspace', '');
      }
      if (key.endsWith('_scheduled')) {
        return key.replace('_scheduled', '');
      }
      return key;
    },
    [treeData, selectedTaskId]
  );

  const normalizeFolderIdForCreate = useCallback(
    (key: string | null): string | null => {
      if (!key) return null;
      const foldersInfo = treeData?.data?.folders || {};
      const info: any = (foldersInfo as any)[key];
      const folderType = info?.folder_type;
      if (folderType === 'workspace' || folderType === 'scheduled') {
        return null;
      }
      if (key.endsWith('_workspace') || key.endsWith('_scheduled')) {
        return null;
      }
      // 若無 mapping 且 key 等於當前 task（通常表示 root），不要誤當成 folder_id
      if ((!foldersInfo || Object.keys(foldersInfo as any).length === 0) && selectedTaskId && key === selectedTaskId) {
        return null;
      }
      return key;
    },
    [treeData, selectedTaskId]
  );

  const openNewFileModalForFolderKey = useCallback(
    (folderKey: string | null, folderName: string | null) => {
      const resolvedTaskId = resolveTaskIdFromFolderKey(folderKey);
      let resolvedFolderId = normalizeFolderIdForCreate(folderKey);
      // 防呆：若 folder_id 恰好等於 task_id，視為 root
      if (resolvedFolderId && resolvedTaskId && resolvedFolderId === resolvedTaskId) {
        resolvedFolderId = null;
      }
      // 修正：FileTree 的 tree key，workspace 使用 `${taskId}_workspace`
      // - 一般 folder：containerKey = folderId
      // - workspace node（xxx_workspace）：containerKey = folderKey
      // - header create（folderKey=null）：containerKey = `${taskId}_workspace`
      let derivedContainerKey: string | null =
        resolvedFolderId || folderKey || (resolvedTaskId ? `${resolvedTaskId}_workspace` : null);
      // 若使用者在「任務節點(root)」點新增，實際放到 workspace 容器
      if (
        derivedContainerKey &&
        resolvedTaskId &&
        derivedContainerKey === resolvedTaskId &&
        !derivedContainerKey.endsWith('_workspace') &&
        !derivedContainerKey.endsWith('_scheduled')
      ) {
        derivedContainerKey = `${resolvedTaskId}_workspace`;
      }
      setNewFileTarget({
        taskId: resolvedTaskId,
        folderId: resolvedFolderId,
        folderLabel: folderName,
        containerKey: derivedContainerKey,
      });
      setShowNewFileModal(true);
    },
    [resolveTaskIdFromFolderKey, normalizeFolderIdForCreate]
  );

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


    // 修改時間：2025-12-14 14:10:04 (UTC+8) - 草稿檔支持所有操作（與正式檔案無異）
    // 草稿檔的操作會更新 localStorage，正式檔案的操作會調用後端 API
    const isDraft = isDraftFileId(contextMenu.fileId);

    // 對於草稿檔的特殊處理（如果需要）
    if (isDraft && action === 'reupload') {
      // 草稿檔不支持重新上傳（尚未提交後端）
      setNotification({ message: '草稿檔尚未提交後端，無法重新上傳', type: 'warning' });
      setTimeout(() => setNotification(null), 3000);
      closeContextMenu();
      return;
    }

    if (isDraft && action === 'viewVectors') {
      // 草稿檔不支持查看向量資料（尚未提交後端）
      setNotification({ message: '草稿檔尚未提交後端，無法查看向量資料', type: 'warning' });
      setTimeout(() => setNotification(null), 3000);
      closeContextMenu();
      return;
    }

    if (isDraft && action === 'viewGraph') {
      // 草稿檔不支持查看圖譜資料（尚未提交後端）
      setNotification({ message: '草稿檔尚未提交後端，無法查看圖譜資料', type: 'warning' });
      setTimeout(() => setNotification(null), 3000);
      closeContextMenu();
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
        // 修改時間：2025-12-14 14:10:04 (UTC+8) - 實現移動目錄功能（支持草稿檔）
        // 查找文件所在的 taskId
        let moveFileTaskId: string | null = null;

        // 如果是草稿檔，從 localStorage 中查找
        if (isDraft) {
          for (const [, drafts] of Object.entries(draftFilesByContainerKey || {})) {
            const draft = (drafts || []).find((d: any) => d?.file_id === contextMenu.fileId);
            if (draft) {
              moveFileTaskId = String(draft?.task_id || selectedTaskId || taskId || '').trim() || null;
              break;
            }
          }
        } else if (treeData?.data?.tree) {
          // 正式檔案：從 treeData 中查找
          for (const [taskId, files] of Object.entries(treeData.data.tree)) {
            if (files.some((f: any) => f.file_id === contextMenu.fileId)) {
              moveFileTaskId = taskId;
              break;
            }
          }
        }

        setMoveFileTarget({
          fileId: contextMenu.fileId,
          fileName: contextMenu.fileName,
          currentTaskId: moveFileTaskId,
          isDraft: isDraft, // 標記是否為草稿檔
        });
        setShowMoveModal(true);
        break;
      case 'delete':
        // 修改時間：2025-12-08 13:30:00 UTC+8 - 實現刪除文件功能，顯示確認對話框
        setDeleteFileTarget({
          fileId: contextMenu.fileId,
          fileName: contextMenu.fileName,
        });
        setShowDeleteFileModal(true);
        break;
      case 'reupload':
        // 修改時間：2025-12-08 13:30:00 UTC+8 - 實現重新上傳文件功能
        // 查找文件所在的 taskId
        let reuploadFileTaskId: string | null = null;
        if (treeData?.data?.tree) {
          for (const [taskId, files] of Object.entries(treeData.data.tree)) {
            if (files.some((f: any) => f.file_id === contextMenu.fileId)) {
              reuploadFileTaskId = taskId;
              break;
            }
          }
        }
        setReuploadFileTarget({
          fileId: contextMenu.fileId,
          fileName: contextMenu.fileName,
          taskId: reuploadFileTaskId,
        });
        setShowReuploadModal(true);
        break;
      case 'copy':
        // TODO: 實現複製功能
        // TODO: 實現複製功能
        break;
      case 'copyPath':
        // 修改時間：2025-12-14 14:10:04 (UTC+8) - 複製可見的文件目錄架構路徑（支持草稿檔）
        // 從 treeData 或 localStorage 中查找文件所屬的 task_id
        let copyPathFileTaskId: string | null = null;
        let copyPathContainerKey: string | null = null;

        // 如果是草稿檔，從 localStorage 中查找
        if (isDraft) {
          for (const [containerKey, drafts] of Object.entries(draftFilesByContainerKey || {})) {
            const draft = (drafts || []).find((d: any) => d?.file_id === contextMenu.fileId);
            if (draft) {
              copyPathFileTaskId = String(draft?.task_id || selectedTaskId || taskId || '').trim() || null;
              copyPathContainerKey = containerKey;
              break;
            }
          }
        } else if (treeData?.data?.tree) {
          // 正式檔案：從 treeData 中查找
          for (const [taskId, files] of Object.entries(treeData.data.tree)) {
            if (files.some((f: any) => f.file_id === contextMenu.fileId)) {
              copyPathFileTaskId = taskId;
              copyPathContainerKey = taskId;
              break;
            }
          }
        }

        // 構建完整的目錄路徑（遞歸查找父資料夾）
        const buildFolderPath = (taskId: string, folders: Record<string, any>): string[] => {
          const path: string[] = [];
          let currentTaskId: string | null = taskId;

          // 如果是 temp-workspace，直接返回
          if (currentTaskId === TEMP_WORKSPACE_ID) {
            return [TEMP_WORKSPACE_NAME];
          }

          // 遞歸查找父資料夾
          const visited = new Set<string>(); // 防止循環引用
          while (currentTaskId && currentTaskId !== TEMP_WORKSPACE_ID && !visited.has(currentTaskId)) {
            visited.add(currentTaskId);
            const folderInfo: any = folders[currentTaskId];
            if (folderInfo) {
              path.unshift(folderInfo.folder_name); // 從前面插入，保持順序
              currentTaskId = folderInfo.parent_task_id;
            } else {
              // 如果找不到資料夾信息，使用 taskId 作為名稱
              path.unshift(currentTaskId);
              break;
            }
          }

          // 如果父資料夾是 null 或 temp-workspace，在路徑前面加上「任務工作區」
          if (currentTaskId === null || currentTaskId === TEMP_WORKSPACE_ID) {
            path.unshift(TEMP_WORKSPACE_NAME);
          }

          return path;
        };

        // 構建文件路徑
        let filePath: string;
        if (copyPathFileTaskId && copyPathContainerKey) {
          const folders = treeData?.data?.folders || {};
          // 如果是草稿檔且 containerKey 是 workspace，使用 TEMP_WORKSPACE_NAME
          if (isDraft && copyPathContainerKey.endsWith('_workspace')) {
            filePath = TEMP_WORKSPACE_NAME + '/' + contextMenu.fileName;
          } else {
            const folderPath = buildFolderPath(copyPathFileTaskId, folders);
            filePath = folderPath.join('/') + '/' + contextMenu.fileName;
          }
        } else {
          // 如果找不到 taskId，只顯示文件名
          filePath = contextMenu.fileName;
        }

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
        // 修改時間：2025-12-14 14:10:04 (UTC+8) - 實現標註到AI任務指令區功能（支持草稿檔）
        // 查找文件所在的 taskId 和路徑
        let attachFileTaskId: string | null = null;
        let attachFilePath: string = '';

        // 如果是草稿檔，從 localStorage 中查找
        if (isDraft) {
          for (const [containerKey, drafts] of Object.entries(draftFilesByContainerKey || {})) {
            const draft = (drafts || []).find((d: any) => d?.file_id === contextMenu.fileId);
            if (draft) {
              attachFileTaskId = String(draft?.task_id || selectedTaskId || taskId || '').trim() || null;

              // 構建文件路徑
              if (containerKey.endsWith('_workspace')) {
                attachFilePath = TEMP_WORKSPACE_NAME;
              } else {
                // 查找資料夾信息
                const folderInfo = treeData?.data?.folders?.[containerKey];
                if (folderInfo) {
                  attachFilePath = folderInfo.folder_name;
                } else {
                  attachFilePath = containerKey;
                }
              }
              break;
            }
          }
        } else if (treeData?.data?.tree) {
          // 正式檔案：從 treeData 中查找
          for (const [taskId, files] of Object.entries(treeData.data.tree)) {
            const file = files.find((f: any) => f.file_id === contextMenu.fileId);
            if (file) {
              attachFileTaskId = taskId === TEMP_WORKSPACE_ID ? null : taskId;

              // 構建文件路徑
              if (taskId === TEMP_WORKSPACE_ID) {
                attachFilePath = TEMP_WORKSPACE_NAME;
              } else {
                // 查找資料夾信息
                const folderInfo = treeData.data.folders?.[taskId];
                if (folderInfo) {
                  attachFilePath = folderInfo.folder_name;
                } else {
                  attachFilePath = taskId;
                }
              }
              break;
            }
          }
        }

        // 觸發文件附加事件
        window.dispatchEvent(new CustomEvent('fileAttachToChat', {
          detail: {
            fileId: contextMenu.fileId,
            fileName: contextMenu.fileName,
            filePath: attachFilePath,
            taskId: attachFileTaskId,
            isDraft: isDraft, // 標記是否為草稿檔
          },
        }));

        setNotification({ message: `已將「${contextMenu.fileName}」標註到任務指令區`, type: 'success' });
        setTimeout(() => setNotification(null), 3000);
        break;
      case 'viewVectors':
        // 修改時間：2025-12-09 - 實現查看向量資料功能
        // 從 treeData 或 fileTree 中查找文件元數據
        let vectorFileMetadata: FileMetadata | null = null;

        // 優先從 treeData 中查找
        if (treeData?.data?.tree) {
          for (const files of Object.values(treeData.data.tree)) {
            const file = (files as any[]).find((f: any) => f.file_id === contextMenu.fileId);
            if (file) {
              vectorFileMetadata = {
                file_id: file.file_id,
                filename: file.filename || contextMenu.fileName,
                file_type: file.file_type || 'application/octet-stream',
                file_size: file.file_size || 0,
                user_id: file.user_id || '',
                task_id: file.task_id || undefined,
                tags: file.tags || [],
                upload_time: file.created_at || file.upload_time || new Date().toISOString(),
                created_at: file.created_at,
                updated_at: file.updated_at,
              };
              break;
            }
          }
        }

        // 如果 treeData 中找不到，嘗試從 fileTree prop 中查找
        if (!vectorFileMetadata && fileTree) {
          const findFileInTree = (nodes: FileNode[]): FileNode | null => {
            for (const node of nodes) {
              if (node.id === contextMenu.fileId && node.type === 'file') {
                return node;
              }
              if (node.children) {
                const found = findFileInTree(node.children);
                if (found) return found;
              }
            }
            return null;
          };
          const fileNode = findFileInTree(fileTree);
          if (fileNode) {
            vectorFileMetadata = {
              file_id: fileNode.id,
              filename: fileNode.name,
              file_type: 'application/octet-stream',
              file_size: 0,
              user_id: '',
              task_id: taskId || undefined,
              tags: [],
              upload_time: new Date().toISOString(),
            };
          }
        }

        // 如果都找不到，使用基本信息創建
        if (!vectorFileMetadata) {
          vectorFileMetadata = {
            file_id: contextMenu.fileId,
            filename: contextMenu.fileName,
            file_type: 'application/octet-stream',
            file_size: 0,
            user_id: '',
            task_id: taskId || undefined,
            tags: [],
            upload_time: new Date().toISOString(),
          };
        }
        setPreviewFile(vectorFileMetadata);
        setPreviewMode('vector');
        setShowDataPreview(true);
        break;
      case 'viewGraph':
        // 修改時間：2025-12-09 - 實現查看圖譜資料功能
        // 從 treeData 或 fileTree 中查找文件元數據
        let graphFileMetadata: FileMetadata | null = null;

        // 優先從 treeData 中查找
        if (treeData?.data?.tree) {
          for (const files of Object.values(treeData.data.tree)) {
            const file = (files as any[]).find((f: any) => f.file_id === contextMenu.fileId);
            if (file) {
              graphFileMetadata = {
                file_id: file.file_id,
                filename: file.filename || contextMenu.fileName,
                file_type: file.file_type || 'application/octet-stream',
                file_size: file.file_size || 0,
                user_id: file.user_id || '',
                task_id: file.task_id || undefined,
                tags: file.tags || [],
                upload_time: file.created_at || file.upload_time || new Date().toISOString(),
                created_at: file.created_at,
                updated_at: file.updated_at,
              };
              break;
            }
          }
        }

        // 如果 treeData 中找不到，嘗試從 fileTree prop 中查找
        if (!graphFileMetadata && fileTree) {
          const findFileInTree = (nodes: FileNode[]): FileNode | null => {
            for (const node of nodes) {
              if (node.id === contextMenu.fileId && node.type === 'file') {
                return node;
              }
              if (node.children) {
                const found = findFileInTree(node.children);
                if (found) return found;
              }
            }
            return null;
          };
          const fileNode = findFileInTree(fileTree);
          if (fileNode) {
            graphFileMetadata = {
              file_id: fileNode.id,
              filename: fileNode.name,
              file_type: 'application/octet-stream',
              file_size: 0,
              user_id: '',
              task_id: taskId || undefined,
              tags: [],
              upload_time: new Date().toISOString(),
            };
          }
        }

        // 如果都找不到，使用基本信息創建
        if (!graphFileMetadata) {
          graphFileMetadata = {
            file_id: contextMenu.fileId,
            filename: contextMenu.fileName,
            file_type: 'application/octet-stream',
            file_size: 0,
            user_id: '',
            task_id: taskId || undefined,
            tags: [],
            upload_time: new Date().toISOString(),
          };
        }
        setPreviewFile(graphFileMetadata);
        setPreviewMode('graph');
        setShowDataPreview(true);
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
  }, [contextMenu, closeContextMenu, treeData, fileTree, taskId]);

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
        // 修改時間：2025-12-14 12:03:00 (UTC+8) - 新增檔案：同一個 modal 支援「空白 .md」或「上傳文件」
        openNewFileModalForFolderKey(
          folderContextMenu.taskId,
          folderContextMenu.taskName || null
        );
        break;
      case 'copyPath':
        // 修改時間：2025-12-08 11:10:00 UTC+8 - 複製可見的資料夾目錄架構路徑
        // 構建完整的目錄路徑（遞歸查找父資料夾）
        const buildFolderPathForCopy = (taskId: string, folders: Record<string, any>): string[] => {
          const path: string[] = [];
          let currentTaskId: string | null = taskId;

          // 如果是 temp-workspace，直接返回
          if (currentTaskId === TEMP_WORKSPACE_ID) {
            return [TEMP_WORKSPACE_NAME];
          }

          // 遞歸查找父資料夾
          const visited = new Set<string>(); // 防止循環引用
          while (currentTaskId && currentTaskId !== TEMP_WORKSPACE_ID && !visited.has(currentTaskId)) {
            visited.add(currentTaskId);
            const folderInfo: any = folders[currentTaskId];
            if (folderInfo) {
              path.unshift(folderInfo.folder_name); // 從前面插入，保持順序
              currentTaskId = folderInfo.parent_task_id;
            } else {
              // 如果找不到資料夾信息，使用 taskId 作為名稱
              path.unshift(currentTaskId);
              break;
            }
          }

          // 如果父資料夾是 null 或 temp-workspace，在路徑前面加上「任務工作區」
          if (currentTaskId === null || currentTaskId === TEMP_WORKSPACE_ID) {
            path.unshift(TEMP_WORKSPACE_NAME);
          }

          return path;
        };

        // 構建資料夾路徑
        const folders = treeData?.data?.folders || {};
        const folderPathArray = buildFolderPathForCopy(folderContextMenu.taskId, folders);
        const folderPath = folderPathArray.join('/');

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
        // 實現剪下資料夾功能
        if (folderContextMenu.taskId === TEMP_WORKSPACE_ID) {
          setNotification({ message: '任務工作區是系統預設的工作區，無法剪下。', type: 'error' });
          setTimeout(() => setNotification(null), 3000);
          break;
        }
        // 將資料夾保存到剪貼板（類型為 cut）
        const folderClipboardItems: ClipboardItem[] = [{
          id: folderContextMenu.taskId,
          type: 'folder',
          name: folderContextMenu.taskName,
        }];
        cutItems(folderClipboardItems);
        setNotification({ message: '資料夾已剪下', type: 'success' });
        setTimeout(() => setNotification(null), 3000);
        break;
      case 'paste':
        // 實現貼上到資料夾功能
        const clipboardState = loadClipboardState();
        if (!clipboardState || clipboardState.items.length === 0) {
          setNotification({ message: '剪貼板為空', type: 'warning' });
          setTimeout(() => setNotification(null), 3000);
          break;
        }

        // 目標父資料夾ID（當前資料夾）
        const targetParentId = folderContextMenu.taskId === TEMP_WORKSPACE_ID ? null : folderContextMenu.taskId;

        // 處理剪貼板中的每個項目
        clipboardState.items.forEach((item) => {
          if (item.type === 'folder') {
            // 檢查是否嘗試移動到自己或子資料夾
            if (item.id === folderContextMenu.taskId) {
              setNotification({ message: '不能將資料夾移動到自己內部', type: 'error' });
              setTimeout(() => setNotification(null), 3000);
              return;
            }

            if (clipboardState.type === 'cut') {
              // 移動資料夾
              moveFolder(item.id, targetParentId)
                .then((result) => {
                  if (result.success) {
                    setNotification({ message: '資料夾已移動', type: 'success' });
                    setTimeout(() => setNotification(null), 3000);
                    // 清除剪貼板
                    clearClipboardState();
                    // 觸發文件樹更新
                    window.dispatchEvent(new CustomEvent('fileTreeUpdated'));
                  } else {
                    setNotification({ message: result.message || '移動資料夾失敗', type: 'error' });
                    setTimeout(() => setNotification(null), 3000);
                  }
                })
                .catch((error) => {
                  console.error('移動資料夾失敗:', error);
                  setNotification({ message: error.message || '移動資料夾失敗', type: 'error' });
                  setTimeout(() => setNotification(null), 3000);
                });
            } else if (clipboardState.type === 'copy') {
              // TODO: 實現複製資料夾功能（需要創建新資料夾並複製所有文件）
              setNotification({ message: '複製資料夾功能尚未實現', type: 'warning' });
              setTimeout(() => setNotification(null), 3000);
            }
          }
        });
        break;
      case 'rename':
        // 檢查是否為 temp-workspace（不允許重命名）
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
  }, [folderContextMenu, closeFolderContextMenu, openNewFileModalForFolderKey]);

  const loadTree = useCallback(async () => {
    // 修改時間：2025-12-09 - 在函數開始時立即檢查 fileTree prop
    // 使用最新的 fileTree 值（通過閉包獲取）
    const currentFileTree = fileTree; // 從閉包獲取最新的 fileTree
    console.log('[FileTree] loadTree called', {
      taskId,
      userId,
      hasFileTree: !!currentFileTree,
      fileTreeLength: currentFileTree?.length,
      fileTreeIsUndefined: currentFileTree === undefined,
      fileTreeIds: currentFileTree?.map(f => f.id) || []
    });

    // 修改時間：2025-12-09 - 如果有 fileTree prop 且不為空，絕對不調用 API
    // fileTree prop 是數據源，不需要從 API 獲取
    // 但如果 fileTree 為 undefined 或空數組，應該從 API 加載
    if (currentFileTree !== undefined && currentFileTree.length > 0) {
      console.log('[FileTree] Using fileTree prop, skipping API call in loadTree', {
        fileTreeLength: currentFileTree.length,
        fileIds: currentFileTree.map(f => f.id)
      });
      setTreeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    // 修改時間：2025-12-08 13:30:00 UTC+8 - 始終加載所有文件，不管是否有 taskId
    // 這樣可以確保文件樹始終顯示完整的目錄結構，包括任務工作區和其他文件夾
    // 如果沒有 userId，不調用 API
    if (!userId) {
      console.log('[FileTree] No userId, skipping API call');
      setTreeData(null);
      setLoading(false);
      return;
    }

    // 檢查是否有模擬文件（歷史任務）- 只在有 taskId 時檢查
    if (taskId && hasMockFiles(taskId)) {
      setLoading(true);
      setError(null);
      try {
        const mockFiles = getMockFiles(taskId);
        // 將模擬文件轉換為 FileTreeResponse 格式
        // 修改時間：2025-12-08 09:32:31 UTC+8 - 修復類型錯誤，添加缺少的 tags 屬性
        const mockResponse: FileTreeResponse = {
          success: true,
          data: {
            tree: {
              [taskId as string]: mockFiles.map(file => ({
                file_id: file.file_id,
                filename: file.filename,
                file_type: file.file_type,
                file_size: file.file_size,
                user_id: file.user_id,
                task_id: file.task_id,
                upload_time: file.upload_time,
                tags: (file as any).tags || [], // 修改時間：2025-12-08 09:32:31 UTC+8 - MockFileMetadata 沒有 tags 屬性，使用類型斷言
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
      // 修改時間：2025-01-27 - 重構任務工作區邏輯
      // 必須提供 taskId 才能查詢文件（文件必須關聯到任務工作區）
      // 如果沒有 taskId，不應該調用 API（新任務尚未創建）
      if (!taskId) {
        console.log('[FileTree] No taskId provided, skipping API call (new task not yet created)');
        setTreeData(null);
        setLoading(false);
        setError(null);
        return;
      }

      console.log('[FileTree] Calling getFileTree API', { userId, taskId });
      const startTime = Date.now();
      const response = await Promise.race([
        getFileTree({ user_id: userId, task_id: taskId }), // taskId 必須存在
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('API request timeout after 30 seconds')), 30000)
        )
      ]) as any;
      const duration = Date.now() - startTime;
      console.log(`[FileTree] getFileTree response received (${duration}ms):`, { success: response?.success, hasData: !!response?.data });
      if (response.success && response.data) {
        console.log('[FileTree] File tree loaded successfully', {
          totalTasks: response.data.total_tasks,
          totalFiles: response.data.total_files,
          treeKeys: Object.keys(response.data.tree || {}),
        });
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
  }, [userId, taskId]); // 移除 fileTree 依賴，避免在 loadTree 內部檢查

  // 修改時間：2025-12-09 - 監聽文件上傳完成事件，不自動刷新（由父組件通過 fileTree prop 更新）
  // 如果有 fileTree prop，不需要監聽這些事件，因為父組件會通過 prop 更新文件樹
  // 如果沒有 fileTree prop，才需要從 API 重新加載
  useEffect(() => {
    // 修改時間：2025-01-27 - 使用 useRef 獲取最新的 fileTree prop 值
    const currentFileTree = fileTreeRef_current.current;

    // 如果有 fileTree prop，不監聽上傳事件（由父組件管理）
    if (currentFileTree && currentFileTree.length > 0) {
      console.log('[FileTree] Has fileTree prop, skipping upload event listeners', {
        fileTreeLength: currentFileTree.length
      });
      return;
    }

    const handleFileUploaded = (event: CustomEvent) => {
      const detail = event.detail;
      const uploadedTaskId = detail?.taskId as string | undefined;
      // 修改時間：2025-12-12 - fileUploaded 現在也會帶 taskId，若符合當前任務或當前未選任務，則刷新並可自動切換
      if (uploadedTaskId) {
        if (!taskId || uploadedTaskId === taskId) {
          console.log('[FileTree] File uploaded event received, reloading tree', { taskId: uploadedTaskId, fileIds: detail.fileIds });
        // 延遲一小段時間，確保後端數據已保存
          setTimeout(() => {
            loadTree();
          }, 500);
        }
        // 若目前沒有選中任務，嘗試自動切換到剛上傳的任務
        if (!taskId && onTaskSelect) {
          onTaskSelect(uploadedTaskId);
        }
      } else if (taskId) {
        // 向後兼容：舊事件只有 fileIds（無 taskId），如果當前有 taskId 就刷新
        console.log('[FileTree] File uploaded (legacy) event received, reloading tree', { taskId, fileIds: detail.fileIds });
        setTimeout(() => {
          loadTree();
        }, 500);
      }
    };

    const handleFilesUploaded = (event: CustomEvent) => {
      const detail = event.detail;
      // filesUploaded 事件包含 taskId，這是主要的刷新觸發點
      if (detail.taskId) {
        // 如果指定了 taskId，檢查是否匹配當前任務
        if (taskId && detail.taskId === taskId) {
          console.log('[FileTree] Files uploaded to current task, reloading tree', { taskId: detail.taskId, fileCount: detail.files?.length });
          setTimeout(() => {
            loadTree();
          }, 500);
        } else if (!taskId) {
          // 如果當前沒有 taskId，但有上傳事件（可能是新任務創建），也刷新
          console.log('[FileTree] Files uploaded (new task), reloading tree', { uploadedTaskId: detail.taskId });
          setTimeout(() => {
            loadTree();
          }, 500);
        }
      }
    };

    // 監聽文件上傳完成事件
    window.addEventListener('fileUploaded', handleFileUploaded as EventListener);
    window.addEventListener('filesUploaded', handleFilesUploaded as EventListener);

    return () => {
      window.removeEventListener('fileUploaded', handleFileUploaded as EventListener);
      window.removeEventListener('filesUploaded', handleFilesUploaded as EventListener);
    };
  }, [taskId, loadTree]); // 移除 fileTree 依賴，使用 fileTreeRef_current.current 獲取最新值

  // 修改時間：2025-12-09 - 監聽 fileTree prop 的變化，強制重新渲染
  // 當 fileTree prop 更新時，FileTree 組件應該自動重新渲染（React 會處理 prop 變化）
  // 但為了確保文件樹能正確顯示，我們記錄 fileTree 的變化
  // 修改時間：2025-12-09 - 監聽 fileTree prop 的變化，強制清除 treeData 以觸發重新渲染
  // 使用 ref 來追蹤 fileTree 的變化
  const prevFileTreeHashRef = useRef<string>('');

  useEffect(() => {
    if (fileTree && fileTree.length > 0) {
      const currentHash = fileTree.map(f => `${f.id}:${f.name}`).sort().join('|');
      const hashChanged = currentHash !== prevFileTreeHashRef.current;

      console.log('[FileTree] fileTree prop updated (useEffect)', {
        taskId,
        fileTreeLength: fileTree.length,
        fileIds: fileTree.map(f => f.id),
        fileNames: fileTree.map(f => f.name),
        fileTreeHash: currentHash,
        previousHash: prevFileTreeHashRef.current,
        hashChanged,
        timestamp: Date.now()
      });

      // 更新 hash 引用
      prevFileTreeHashRef.current = currentHash;

      // 清除 treeData，強制使用 fileTree prop（避免混用兩種數據源）
      setTreeData(null);
      setLoading(false);
      setError(null);
    } else if (!fileTree || fileTree.length === 0) {
      // 如果 fileTree prop 為空或不存在，清除 treeData，讓組件從 API 獲取
      if (taskId) {
        console.log('[FileTree] fileTree prop is empty, will load from API', { taskId });
        // 不立即調用 loadTree，讓下面的 useEffect 處理
      } else {
        console.log('[FileTree] No fileTree prop and no taskId, clearing treeData');
        setTreeData(null);
        setLoading(false);
        setError(null);
      }
      prevFileTreeHashRef.current = '';
    }
  }, [fileTree, taskId]);

  // 修改時間：2025-01-27 - 更新 fileTreeRef_current 當 fileTree prop 變化時
  useEffect(() => {
    fileTreeRef_current.current = fileTree;
  }, [fileTree]);

  useEffect(() => {
    console.log('[FileTree] useEffect triggered (loadTree check)', {
      taskId,
      userId,
      hasFileTree: !!fileTree,
      fileTreeLength: fileTree?.length,
      fileTreeIsUndefined: fileTree === undefined,
      hasTreeData: !!treeData
    });

    // 修改時間：2025-12-09 - 如果有 fileTree prop 且不為空，絕對不調用 API
    // fileTree prop 是數據源，不需要從 API 獲取
    // 但如果 fileTree 為 undefined 或空數組，應該從 API 加載
    if (fileTree !== undefined && fileTree.length > 0) {
      console.log('[FileTree] Using fileTree prop, skipping API call completely', {
        fileTreeLength: fileTree.length,
        fileIds: fileTree.map(f => f.id)
      });
      setLoading(false);
      setError(null);
      // 確保 treeData 為 null，強制使用 fileTree prop
      if (treeData !== null) {
        console.log('[FileTree] Clearing treeData to force use of fileTree prop');
        setTreeData(null);
      }
      return;
    }

    // 修改時間：2025-01-27 - 新任務尚未創建時，不調用 API
    // 如果沒有 taskId（新任務尚未真正創建），且沒有 fileTree prop，直接返回空狀態
    if (!taskId) {
      console.log('[FileTree] No taskId provided (new task not yet created), skipping API call');
      setTreeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    // 如果沒有 userId，不調用 loadTree
    if (!userId) {
      console.log('[FileTree] No userId, skipping loadTree');
      setTreeData(null);
      setLoading(false);
      setError(null);
      return;
    }

    // 修改時間：2025-12-09 - 如果 fileTree 為 undefined 或空數組，從 API 加載
    // 這樣可以確保清除 localStorage 後，文件樹能正確從後端加載
    if (fileTree === undefined || (Array.isArray(fileTree) && fileTree.length === 0)) {
      console.log('[FileTree] fileTree is undefined or empty, calling loadTree from API', {
        userId,
        taskId,
        fileTreeIsUndefined: fileTree === undefined,
        fileTreeIsArray: Array.isArray(fileTree),
        fileTreeLength: fileTree?.length || 0,
        fileTreeValue: fileTree
      });
      // 確保調用 loadTree
      loadTree().catch((error) => {
        console.error('[FileTree] loadTree failed:', error);
        setError(error.message || '加載文件樹失敗');
        setLoading(false);
      });
    } else {
      console.log('[FileTree] fileTree has content, skipping API call', {
        fileTreeLength: fileTree?.length,
        fileTreeIsUndefined: fileTree === undefined
      });
    }
  }, [userId, taskId, fileTree, loadTree]); // 添加 loadTree 依賴

  // 監聽文件樹更新事件
  useEffect(() => {
    const handleFileTreeUpdate = (event: Event) => {
      // 修改時間：2025-01-27 - 使用 useRef 獲取最新的 fileTree prop 值
      // 這樣可以確保即使事件監聽器中的閉包是舊的，也能訪問到最新的 fileTree
      const currentFileTree = fileTreeRef_current.current;
      console.log('[FileTree] handleFileTreeUpdate triggered', {
        taskId,
        hasFileTree: !!currentFileTree,
        fileTreeLength: currentFileTree?.length,
        fileTreeIds: currentFileTree?.map(f => f.id) || []
      });

      // 如果有 fileTree prop，但處於強制重載/抑制回退模式，仍允許重載
      const forceReload = (event as CustomEvent)?.detail?.forceReload;
      if (currentFileTree && currentFileTree.length > 0 && !forceReload && !suppressPropFallback) {
        console.log('[FileTree] Has fileTree prop, skipping API reload (fileTree managed by parent)', {
          fileTreeLength: currentFileTree.length,
          fileTreeIds: currentFileTree.map(f => f.id)
        });
        return;
      }

      // 如果沒有 taskId，不能調用 API（後端要求必須提供 task_id）
      if (!taskId) {
        console.log('[FileTree] No taskId, cannot reload from API');
        return;
      }

      // 只有在沒有 fileTree prop 時，才從 API 重新加載
      console.log('[FileTree] Reloading file tree from API (no fileTree prop or forceReload)', { taskId, userId, forceReload, suppressPropFallback });
      setLoading(true);
      setError(null);
      getFileTree({ user_id: userId, task_id: taskId })
        .then((response) => {
          console.log('[FileTree] File tree reloaded after update', { success: response.success });
          if (response.success && response.data) {
            setTreeData(response);
            setLatestTreeData(response);
          } else {
            setError('無法加載文件樹');
          }
        })
        .catch((err: any) => {
          console.error('[FileTree] Error loading file tree:', err);
          setError(err.message || '加載文件樹失敗');
        })
        .finally(() => {
          setLoading(false);
        });
    };

    // 修改時間：2025-12-08 08:46:00 UTC+8 - 添加用戶登錄事件監聽，登錄後清除緩存並重新加載文件樹
    // 監聽用戶登錄事件，登錄後清除緩存並重新加載文件樹
    const handleUserLoggedIn = () => {
      // 修改時間：2025-01-27 - 使用 useRef 獲取最新的 fileTree prop 值
      const currentFileTree = fileTreeRef_current.current;
      console.log('[FileTree] User logged in, clearing cache and reloading file tree', {
        hasFileTree: !!currentFileTree,
        fileTreeLength: currentFileTree?.length
      });
      // 如果有 fileTree prop，不需要重新加載（由父組件管理）
      if (currentFileTree && currentFileTree.length > 0) {
        console.log('[FileTree] Has fileTree prop, skipping reload on user login');
        return;
      }
      // 清除文件樹緩存，強制從後台加載最新數據
      if (userId) {
        clearFileTreeCache(userId, taskId);
      }
      // 重新加載文件樹（只有在沒有 fileTree prop 時）
      if (taskId) {
        loadTree();
      }
    };

    window.addEventListener('fileTreeUpdated', handleFileTreeUpdate as EventListener);
    window.addEventListener('userLoggedIn', handleUserLoggedIn as EventListener);
    return () => {
      window.removeEventListener('fileTreeUpdated', handleFileTreeUpdate as EventListener);
      window.removeEventListener('userLoggedIn', handleUserLoggedIn as EventListener);
    };
  }, [taskId, userId, loadTree]); // 移除 fileTree 依賴，使用 fileTreeRef_current.current 獲取最新值

  // 修改時間：2025-12-08 13:30:00 UTC+8 - 移除 taskId 檢查，始終顯示文件樹
  // 即使沒有 taskId，也應該顯示文件樹（包括任務工作區）
  // 如果沒有 userId 且沒有 fileTree，顯示空白
  if (!userId && (!fileTree || fileTree.length === 0)) {
    return (
      <div className="p-4 text-sm text-tertiary text-center theme-transition">
        暫無文件
        <br />
        <span className="text-xs text-muted theme-transition">開始輸入或上傳文件後將顯示文件目錄</span>
      </div>
    );
  }

  // 修改時間：2025-12-09 - 渲染時優先使用 API 拉到的 treeData，其次使用最近成功的 latestTreeData；
  // 僅在都沒有時才回退到 fileTree prop，避免移動/上傳時暫時顯示舊資料
  const renderTreeData: FileTreeResponse | null =
    (treeData && treeData.data)
      ? treeData
      : (isReloadingTree && latestTreeData ? latestTreeData : null) ||
        (suppressPropFallback
          ? null
          : (mergedFileTreeForRender && mergedFileTreeForRender.length > 0
              ? buildTreeDataFromFileTree(mergedFileTreeForRender)
              : null));

  // 如果有 renderTreeData，渲染文件樹
  if (renderTreeData?.data) {
    const fileTreeHash = mergedFileTreeForRender
      ? mergedFileTreeForRender.map(f => `${f.id}:${f.name}`).sort().join('|')
      : 'api-tree';
    console.log('[FileTree] Rendering tree', {
      taskId,
      from: treeData ? 'api' : 'prop',
      fileTreeLength: mergedFileTreeForRender?.length,
      treeKeys: Object.keys(renderTreeData.data.tree || {}),
      foldersCount: Object.keys(renderTreeData.data.folders || {}).length,
      fileTreeHash,
      timestamp: Date.now(),
      renderKey: `filetree-${taskId}-${fileTreeHash}`
    });
    const modalTreeData = renderTreeData;

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
              onContextMenu={(e) => {
                // 修改時間：2025-01-27 - 為 fileTree prop 渲染路徑添加右鍵菜單支持
                // 對於文件夾，使用 node.id 作為 taskId，node.name 作為 taskName
                handleFolderContextMenu(e, node.id, node.name);
              }}
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
                if (isDraftFileId(node.id)) {
                  // 修改時間：2025-12-14 13:47:04 (UTC+8) - 草稿檔可直接在前端預覽空檔
                  // 直接調用 onFileSelect，讓它顯示空檔預覽
                  onFileSelect(node.id, node.name);
                  return;
                }
                onFileSelect(node.id, node.name);
              }
            }}
            onContextMenu={(e) => {
              // 修改時間：2025-01-27 - 為 fileTree prop 渲染路徑添加右鍵菜單支持
              handleContextMenu(e, node.id, node.name);
            }}
          >
            <FileIcon className="w-3 h-3 text-tertiary" />
            <span className="flex-1 truncate text-primary">{node.name}</span>
            {isDraftFileId(node.id) && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border border-yellow-500/30">
                草稿
              </span>
            )}
          </div>
        );
      }
    };

    return (
      <>
        <div className="h-full overflow-y-auto">
          <div className="p-4 border-b border-primary theme-transition">
            <h3 className="text-sm font-semibold text-primary mb-1 theme-transition">文件目錄</h3>
            <p className="text-xs text-tertiary theme-transition">
              本地任務文件
            </p>
          </div>
          {(() => {
            const safeFileTree = mergedFileTreeForRender ?? (fileTree ?? []);
            const hash = safeFileTree.map(f => `${f.id}:${f.name}`).sort().join('|');
            return (
          <div
            className="p-2"
            key={`filetree-content-${taskId || 'no-task'}-${hash}`}
          >
            {safeFileTree.map((node, index) => (
              <div key={`filetree-node-${node.id}-${index}-${safeFileTree.length}`}>
                {renderFileNode(node, 0)}
              </div>
            ))}
            {safeFileTree.length === 0 && (
              <div className="p-4 text-sm text-tertiary text-center theme-transition">
                暫無文件
              </div>
            )}
          </div>
            );
          })()}
        </div>

        {/* 修改時間：2025-01-27 - 為 fileTree prop 渲染路徑添加右鍵菜單支持 */}
        {/* 文件右鍵菜單 */}
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
              <span>移動文件目錄</span>
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
              <span>標註到任務指令區</span>
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
            <div className="border-t border-primary my-1"></div>
            <button
              className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/20 hover:text-red-300 theme-transition flex items-center gap-2 transition-colors duration-200"
              onClick={() => handleMenuAction('delete')}
            >
              <i className="fa-solid fa-trash w-4"></i>
              <span>刪除文件</span>
            </button>
            <button
              className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
              onClick={() => handleMenuAction('reupload')}
            >
              <i className="fa-solid fa-upload w-4"></i>
              <span>重新上傳文件</span>
            </button>
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

        {/* 文件信息對話框 */}
        {/* 修改時間：2025-12-09 - 添加文件數據預覽組件 */}
        {showDataPreview && previewFile && (
          <FileDataPreview
            file={previewFile}
            initialMode={previewMode}
            isOpen={showDataPreview}
            onClose={() => {
              setShowDataPreview(false);
              setPreviewFile(null);
            }}
          />
        )}

        {showFileInfoModal && fileInfo && (
          <FileInfoModal
            fileId={fileInfo.fileId}
            fileName={fileInfo.fileName}
            taskId={taskId}
            treeData={treeData}
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

        {/* 刪除文件確認對話框 */}
        {showDeleteFileModal && deleteFileTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
            <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
              <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
                刪除文件
              </h2>
              <p className="text-sm text-tertiary mb-6 theme-transition">
                確定要刪除文件「<span className="text-primary font-semibold">{deleteFileTarget.fileName}</span>」嗎？
                <br />
                <span className="text-red-400">此操作將永久刪除該文件及其相關數據（向量、圖譜、元數據），且無法復原。</span>
              </p>
              <div className="flex justify-end gap-2">
                <button
                  onClick={handleDeleteFileCancel}
                  className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleDeleteFileConfirm}
                  className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
                >
                  確定刪除
                </button>
              </div>
            </div>
          </div>
        )}

        {/* 重新上傳文件確認對話框 */}
        {showReuploadModal && reuploadFileTarget && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
            <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
              <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
                重新上傳文件
              </h2>
              <p className="text-sm text-tertiary mb-6 theme-transition">
                確定要重新上傳文件「<span className="text-primary font-semibold">{reuploadFileTarget.fileName}</span>」嗎？
                <br />
                <span className="text-yellow-400">此操作將先刪除原文件的所有數據（向量、圖譜、元數據、文件），然後打開文件上傳對話框供您選擇新文件。</span>
              </p>
              <div className="flex justify-end gap-2">
                <button
                  onClick={handleReuploadCancel}
                  className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleReuploadConfirm}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
                >
                  確定重新上傳
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

        {/* 修改時間：2025-12-08 09:29:49 UTC+8 - 添加文件移動目錄選擇彈窗 */}
        {showMoveModal && moveFileTarget && (
          <FileMoveModal
            isOpen={showMoveModal}
            onClose={() => {
              setShowMoveModal(false);
              setMoveFileTarget(null);
            }}
            onConfirm={handleMoveConfirm}
            fileId={moveFileTarget.fileId}
            fileName={moveFileTarget.fileName}
            treeData={modalTreeData}
            currentTaskId={moveFileTarget.currentTaskId}
          />
        )}

        {/* 修改時間：2025-12-14 12:58:00 (UTC+8) - 新建檔案 Modal（prop render 分支也需要） */}
        {showNewFileModal && (
          <NewFileOrUploadModal
            isOpen={showNewFileModal}
            onClose={() => {
              setShowNewFileModal(false);
              setNewFileTarget(null);
            }}
            taskId={newFileTarget?.taskId || null}
            folderId={newFileTarget?.folderId || null}
            folderLabel={newFileTarget?.folderLabel || null}
            containerKey={newFileTarget?.containerKey || null}
            existingFilenames={(() => {
              // prop render 分支：只能從本地 draft + fileTree prop 估算（不查後端）
              const ck = (newFileTarget?.containerKey || newFileTarget?.folderId || newFileTarget?.taskId || '').trim();
              const drafts = ck ? (draftFilesByContainerKey as any)?.[ck] : [];
              const draftNames = Array.isArray(drafts) ? drafts.map((d: any) => d?.filename).filter(Boolean) : [];
              const propNames = Array.isArray(fileTree)
                ? fileTree
                    .filter((n: any) => n?.type === 'file')
                    .map((n: any) => n?.name)
                    .filter(Boolean)
                : [];
              return [...propNames, ...draftNames];
            })()}
          />
        )}
      </>
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
    console.log('[FileTree] No treeData or treeData.data', { treeData, hasTreeData: !!treeData, hasData: treeData?.data });
    return (
      <div className="p-4 text-sm text-tertiary theme-transition">
        暫無文件
      </div>
    );
  }

  const { tree, total_tasks, total_files, folders } = treeData.data;
  const getMergedFiles = useCallback(
    (containerKey: string): any[] => {
      const apiFiles = (tree && (tree as any)[containerKey]) ? (tree as any)[containerKey] : [];
      const drafts = (draftFilesByContainerKey && (draftFilesByContainerKey as any)[containerKey])
        ? (draftFilesByContainerKey as any)[containerKey]
        : [];
      return [...(Array.isArray(apiFiles) ? apiFiles : []), ...(Array.isArray(drafts) ? drafts : [])];
    },
    [tree, draftFilesByContainerKey]
  );
  const totalDraftFiles = useMemo(() => {
    try {
      return Object.values(draftFilesByContainerKey || {}).reduce((sum, arr) => sum + (Array.isArray(arr) ? arr.length : 0), 0);
    } catch {
      return 0;
    }
  }, [draftFilesByContainerKey]);
  console.log('[FileTree] Rendering tree', {
    total_tasks,
    total_files,
    treeKeys: Object.keys(tree || {}),
    foldersCount: Object.keys(folders || {}).length,
    hasTempWorkspace: TEMP_WORKSPACE_ID in (tree || {}),
    tempWorkspaceFiles: tree?.[TEMP_WORKSPACE_ID]?.length || 0,
    folders: Object.entries(folders || {}).map(([id, info]: [string, any]) => ({
      id,
      name: info.folder_name,
      parent: info.parent_task_id
    }))
  });
  const foldersInfo = folders || {};

  // 修改時間：2025-12-08 09:32:31 UTC+8 - 將函數定義移到使用之前，修復變數宣告順序錯誤
  // 修改時間：2025-01-27 - 修復頂級資料夾邏輯
  // 獲取頂級資料夾列表（同一任務下的根目錄資料夾，如「任務工作區」和「排程任務」）
  // 修改時間：2025-01-27 - 添加資料夾排序功能（確保 workspace 在前）
  const getTopLevelFolders = (): TreeNode[] => {
    const topLevelFolders: TreeNode[] = [];
    Object.entries(foldersInfo).forEach(([folderTaskId, folderInfo]) => {
      // 修改時間：2025-01-27 - 頂級資料夾的判斷邏輯
      // 頂級資料夾：parent_task_id 為 null 或 undefined，並且屬於當前任務
      // 包括「任務工作區」(folder_type='workspace') 和「排程任務」(folder_type='scheduled')
      const isTopLevel = (folderInfo.parent_task_id === null || folderInfo.parent_task_id === undefined);

      // 如果指定了 taskId，只顯示該任務的頂級資料夾
      if (isTopLevel) {
        // 檢查是否屬於當前任務（透過 _key 判斷）
        const belongsToCurrentTask = taskId ? folderTaskId.startsWith(taskId) : true;

        if (belongsToCurrentTask) {
          topLevelFolders.push({
            taskId: folderTaskId,
            taskName: folderInfo.folder_name,
            fileCount: getMergedFiles(folderTaskId).length,
            isExpanded: expandedTasks.has(folderTaskId),
          });
        }
      }
    });

    // 修改時間：2025-01-27 - 添加資料夾排序：workspace 在前，scheduled 在後
    topLevelFolders.sort((a, b) => {
      // 修改時間：2025-01-27 - 使用類型斷言訪問 folder_type（API 可能返回但類型定義中未包含）
      const aType = (foldersInfo[a.taskId] as any)?.folder_type || '';
      const bType = (foldersInfo[b.taskId] as any)?.folder_type || '';

      // workspace 排在前面
      if (aType === 'workspace' && bType !== 'workspace') return -1;
      if (aType !== 'workspace' && bType === 'workspace') return 1;

      // scheduled 排在 workspace 後面
      if (aType === 'scheduled' && bType !== 'scheduled' && bType !== 'workspace') return -1;
      if (aType !== 'scheduled' && aType !== 'workspace' && bType === 'scheduled') return 1;

      // 其他情況按名稱排序
      return a.taskName.localeCompare(b.taskName);
    });

    return topLevelFolders;
  };

  // 構建任務列表（優先顯示任務工作區）
  const taskList: TreeNode[] = [];

  // 修改時間：2025-01-27 - 重構任務工作區顯示邏輯
  // 顯示該任務的所有頂級資料夾（「任務工作區」和「排程任務」並列）
  if (taskId) {
    // 指定了 taskId，顯示該任務的所有頂級資料夾
    const topLevelFolders = getTopLevelFolders();

    // 將頂級資料夾添加到列表（它們應該並列顯示）
    topLevelFolders.forEach((folder) => {
      taskList.push(folder);
    });
  } else {
    // 未指定 taskId，顯示所有任務的資料夾（向後兼容）
    const topLevelFolders = getTopLevelFolders();
    topLevelFolders.forEach((folder) => {
      taskList.push(folder);
    });

    // 顯示其他任務文件夾（不在 folders 中的，可能是舊的任務ID）
    Object.entries(tree).forEach(([taskIdKey, files]) => {
      if (!foldersInfo[taskIdKey]) {
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
  // 修改時間：2025-01-27 - 修復資料夾層級邏輯，根據 folder_type 區分
  const getSubFolders = (parentTaskId: string): TreeNode[] => {
    const subFolders: TreeNode[] = [];
    Object.entries(foldersInfo).forEach(([folderTaskId, folderInfo]) => {
      // 處理 parent_task_id 可能為 null、undefined 或字符串的情況
      const folderParentId = folderInfo.parent_task_id;

      // 修改時間：2025-01-27 - 修復邏輯
      // 不應該將所有 parent_task_id === null 的資料夾都當作子資料夾
      // 「任務工作區」(folder_type='workspace') 和「排程任務」(folder_type='scheduled') 應該是並列的根目錄
      // 只有當 parent_task_id 明確等於 parentTaskId 時才是子資料夾

      // 匹配邏輯：只匹配 parent_task_id 等於 parentTaskId 的資料夾（真正的子資料夾）
      if (folderParentId === parentTaskId) {
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

  return (
    <div className="h-full overflow-y-auto" ref={fileTreeRef} tabIndex={0}>
      <div className="p-4 border-b border-primary theme-transition">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-primary mb-1 theme-transition">
              文件目錄
            </h3>
            <p className="text-xs text-tertiary theme-transition">
              {total_tasks} 個工作區 • {total_files + totalDraftFiles} 個文件
              {totalDraftFiles > 0 ? `（含 ${totalDraftFiles} 個草稿）` : ''}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              className="px-2 py-1 text-xs border rounded hover:bg-tertiary theme-transition"
              // 修改時間：2025-12-14 13:22:37 (UTC+8) - Header 新增檔案：一律以「目前選取 task root」為準
              onClick={() => openNewFileModalForFolderKey(null, null)}
              title="新增檔案（空白 .md）"
            >
              新增檔案
            </button>
            <button
              className="px-2 py-1 text-xs border rounded hover:bg-tertiary theme-transition"
              onClick={() => {
                // 以目前聚焦 folder 為 parent；未聚焦則 root
                setNewFolderParentId(focusedFolderId);
                setNewFolderInput('');
                setShowNewFolderModal(true);
              }}
              title="新增資料夾"
            >
              新增資料夾
            </button>
          </div>
        </div>
      </div>

      <div className="p-2">
        {taskList.length === 0 ? (
          <div className="p-4 text-sm text-tertiary theme-transition text-center">
            暫無工作區
            <br />
            <span className="text-xs text-muted theme-transition">請創建任務或上傳文件</span>
          </div>
        ) : (
          taskList.map((task) => {
            const isSelected = selectedTaskId === task.taskId;
            const isExpanded = expandedTasks.has(task.taskId);
            const files = getMergedFiles(task.taskId);
            const subFolders = getSubFolders(task.taskId);

            // 修改時間：2025-12-08 13:40:00 UTC+8 - 添加調試信息
            if (task.taskId === TEMP_WORKSPACE_ID) {
              console.log('[FileTree] Rendering task workspace', {
                taskId: task.taskId,
                taskName: task.taskName,
                fileCount: task.fileCount,
                isExpanded,
                filesCount: files.length,
                subFoldersCount: subFolders.length,
                subFolders: subFolders.map(f => ({ id: f.taskId, name: f.taskName, files: tree[f.taskId]?.length || 0 }))
              });
            }

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

              {/* 修改時間：2025-01-27 - 文件應該直接顯示在資料夾節點下 */}
              {/* 展開時顯示：1) 文件列表（如果有） 2) 子資料夾列表（如果有） */}
              {isExpanded && (() => {
                // 文件直接屬於這個資料夾
                const filesInFolder = files || [];
                const subFolders = getSubFolders(task.taskId);

                // 如果沒有文件也沒有子資料夾，不顯示任何內容
                if (filesInFolder.length === 0 && subFolders.length === 0) {
                  return null;
                }

                return (
                  <div className="ml-6 mt-1 space-y-0.5">
                    {/* 文件列表（直接屬於這個資料夾） */}
                    {filesInFolder.length > 0 && (
                      <div className="mb-1">
                        {filesInFolder.slice(0, 20).map((file: any) => (
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
                                if (isDraftFileId(file.file_id)) {
                                  // 修改時間：2025-12-14 13:47:04 (UTC+8) - 草稿檔可直接在前端預覽空檔，不需要 taskId
                                  // 如果有 taskId，可選跳轉文件助手；否則直接顯示空檔預覽
                                  const targetTaskId = String(file?.task_id || selectedTaskId || taskId || '').trim();
                                  if (targetTaskId) {
                                    // 有 taskId：可選跳轉文件助手（但先讓用戶看到空檔預覽）
                                    // 直接調用 onFileSelect，讓它顯示空檔預覽
                                    onFileSelect(file.file_id, file.filename);
                                  } else {
                                    // 無 taskId：直接顯示空檔預覽
                                    onFileSelect(file.file_id, file.filename);
                                  }
                                  return;
                                }
                                onFileSelect(file.file_id, file.filename);
                              }
                            }}
                            onContextMenu={(e) => {
                              handleContextMenu(e, file.file_id, file.filename);
                            }}
                          >
                            <FileIcon className="w-3 h-3 text-tertiary flex-shrink-0" />
                            <span className={`flex-1 truncate ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-primary'}`}>
                              {file.filename}
                            </span>
                            {isDraftFileId(file.file_id) && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border border-yellow-500/30">
                                草稿
                              </span>
                            )}
                          </div>
                        ))}
                        {filesInFolder.length > 20 && (
                          <div className="px-2 py-1 text-xs text-tertiary theme-transition">
                            ...還有 {filesInFolder.length - 20} 個文件
                          </div>
                        )}
                      </div>
                    )}

                    {/* 子資料夾列表（如果有子資料夾） */}
                    {subFolders.length > 0 && (
                      <div className="mt-1">
                        {subFolders.map((subFolder) => {
                          const isSubExpanded = expandedTasks.has(subFolder.taskId);
                          const subFiles = getMergedFiles(subFolder.taskId);
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
                                    const subSubFiles = getMergedFiles(subSubFolder.taskId);
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
                                                    if (isDraftFileId(file.file_id)) {
                                                      // 修改時間：2025-12-14 13:47:04 (UTC+8) - 草稿檔可直接在前端預覽空檔
                                                      onFileSelect(file.file_id, file.filename);
                                                      return;
                                                    }
                                                    onFileSelect(file.file_id, file.filename);
                                                  }
                                                }}
                                                onContextMenu={(e) => {
                                                  handleContextMenu(e, file.file_id, file.filename);
                                                }}
                                              >
                                                <FileIcon className="w-3 h-3 text-tertiary flex-shrink-0" />
                                                <span className={`flex-1 truncate ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-primary'}`}>
                                                  {file.filename}
                                                </span>
                                                {isDraftFileId(file.file_id) && (
                                                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border border-yellow-500/30">
                                                    草稿
                                                  </span>
                                                )}
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
                                      if (isDraftFileId(file.file_id)) {
                                        // 修改時間：2025-12-14 13:47:04 (UTC+8) - 草稿檔可直接在前端預覽空檔
                                        onFileSelect(file.file_id, file.filename);
                                        return;
                                      }
                                      onFileSelect(file.file_id, file.filename);
                                    }
                                  }}
                                  onContextMenu={(e) => {
                                    handleContextMenu(e, file.file_id, file.filename);
                                  }}
                                >
                                  <FileIcon className="w-3 h-3 text-tertiary flex-shrink-0" />
                                  <span className={`flex-1 truncate ${selectedFileId === file.file_id ? 'text-blue-400' : 'text-primary'}`}>
                                    {file.filename}
                                  </span>
                                  {isDraftFileId(file.file_id) && (
                                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 border border-yellow-500/30">
                                      草稿
                                    </span>
                                  )}
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
                    )}
                  </div>
                );
              })()}
            </div>
          );
          })
        )}
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
            <span>移動文件目錄</span>
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
            <span>標註到任務指令區</span>
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
          <div className="border-t border-primary my-1"></div>
          <button
            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/20 hover:text-red-300 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('delete')}
          >
            <i className="fa-solid fa-trash w-4"></i>
            <span>刪除文件</span>
          </button>
          <button
            className="w-full text-left px-4 py-2 text-sm text-primary hover:bg-blue-500/20 hover:text-blue-400 theme-transition flex items-center gap-2 transition-colors duration-200"
            onClick={() => handleMenuAction('reupload')}
          >
            <i className="fa-solid fa-upload w-4"></i>
            <span>重新上傳文件</span>
          </button>
        </div>
      )}

      {/* 修改時間：2025-12-09 - 添加文件數據預覽組件（treeData 路徑） */}
      {showDataPreview && previewFile && (
        <FileDataPreview
          file={previewFile}
          initialMode={previewMode}
          isOpen={showDataPreview}
          onClose={() => {
            setShowDataPreview(false);
            setPreviewFile(null);
          }}
        />
      )}

      {/* 文件信息對話框 */}
      {showFileInfoModal && fileInfo && (
        <FileInfoModal
          fileId={fileInfo.fileId}
          fileName={fileInfo.fileName}
          taskId={taskId}
          treeData={treeData}
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

      {/* 刪除文件確認對話框 */}
      {showDeleteFileModal && deleteFileTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              刪除文件
            </h2>
            <p className="text-sm text-tertiary mb-6 theme-transition">
              確定要刪除文件「<span className="text-primary font-semibold">{deleteFileTarget.fileName}</span>」嗎？
              <br />
              <span className="text-red-400">此操作將永久刪除該文件及其相關數據（向量、圖譜、元數據），且無法復原。</span>
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={handleDeleteFileCancel}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleDeleteFileConfirm}
                className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-colors"
              >
                確定刪除
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 重新上傳文件確認對話框 */}
      {showReuploadModal && reuploadFileTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition">
          <div className="bg-secondary border border-primary rounded-lg shadow-lg w-full max-w-md p-6 theme-transition">
            <h2 className="text-lg font-semibold text-primary mb-4 theme-transition">
              重新上傳文件
            </h2>
            <p className="text-sm text-tertiary mb-6 theme-transition">
              確定要重新上傳文件「<span className="text-primary font-semibold">{reuploadFileTarget.fileName}</span>」嗎？
              <br />
              <span className="text-yellow-400">此操作將先刪除原文件的所有數據（向量、圖譜、元數據、文件），然後打開文件上傳對話框供您選擇新文件。</span>
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={handleReuploadCancel}
                className="px-4 py-2 bg-tertiary hover:bg-hover text-primary rounded-lg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleReuploadConfirm}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors"
              >
                確定重新上傳
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

      {/* 修改時間：2025-12-08 09:29:49 UTC+8 - 添加文件移動目錄選擇彈窗 */}
      {showMoveModal && moveFileTarget && (
        <FileMoveModal
          isOpen={showMoveModal}
          onClose={() => {
            setShowMoveModal(false);
            setMoveFileTarget(null);
          }}
          onConfirm={handleMoveConfirm}
          fileId={moveFileTarget.fileId}
          fileName={moveFileTarget.fileName}
          treeData={modalTreeData}
          currentTaskId={moveFileTarget.currentTaskId}
        />
      )}

      {/* 修改時間：2025-12-14 12:58:00 (UTC+8) - 新建檔案 Modal（只輸入檔名） */}
      {showNewFileModal && (
        <NewFileOrUploadModal
          isOpen={showNewFileModal}
          onClose={() => {
            setShowNewFileModal(false);
            setNewFileTarget(null);
          }}
          taskId={newFileTarget?.taskId || null}
          folderId={newFileTarget?.folderId || null}
          folderLabel={newFileTarget?.folderLabel || null}
          containerKey={newFileTarget?.containerKey || null}
          existingFilenames={(() => {
            const ck = (newFileTarget?.containerKey || newFileTarget?.folderId || newFileTarget?.taskId || '').trim();
            if (!ck) return [];
            const merged = getMergedFiles(ck);
            return Array.isArray(merged) ? merged.map((f: any) => f?.filename).filter(Boolean) : [];
          })()}
        />
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
  // 修改時間：2025-12-08 12:00:00 UTC+8 - 添加 treeData 用於構建路徑
  treeData?: FileTreeResponse | null;
}

function FileInfoModal({ fileId, fileName, taskId, onClose, treeData }: FileInfoModalProps) {
  const [fileMetadata, setFileMetadata] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [hasVectors, setHasVectors] = useState<boolean | null>(null);
  const [hasGraph, setHasGraph] = useState<boolean | null>(null);
  // 修改時間：2025-12-08 12:00:00 UTC+8 - 添加向量和圖譜詳細信息
  const [vectorInfo, setVectorInfo] = useState<{ chunkCount?: number; dimension?: number } | null>(null);
  const [graphInfo, setGraphInfo] = useState<{ nodeCount?: number; tripleCount?: number } | null>(null);
  const [filePath, setFilePath] = useState<string>('');
  const [fileTaskId, setFileTaskId] = useState<string | null>(null);

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
            setFileTaskId(mockFile.task_id);
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
              setFileTaskId(file.task_id || null);

              // 構建文件路徑
              if (treeData?.data?.tree && file.task_id) {
                const buildFolderPath = (taskId: string, folders: Record<string, any>): string[] => {
                  const path: string[] = [];
                  let currentTaskId: string | null = taskId;

                  if (currentTaskId === TEMP_WORKSPACE_ID) {
                    return [TEMP_WORKSPACE_NAME];
                  }

                  const visited = new Set<string>();
                  while (currentTaskId && currentTaskId !== TEMP_WORKSPACE_ID && !visited.has(currentTaskId)) {
                    visited.add(currentTaskId);
                    const folderInfo: any = folders[currentTaskId];
                    if (folderInfo) {
                      path.unshift(folderInfo.folder_name);
                      currentTaskId = folderInfo.parent_task_id;
                    } else {
                      path.unshift(currentTaskId);
                      break;
                    }
                  }

                  if (currentTaskId === null || currentTaskId === TEMP_WORKSPACE_ID) {
                    path.unshift(TEMP_WORKSPACE_NAME);
                  }

                  return path;
                };

                const folders = treeData.data.folders || {};
                const folderPath = buildFolderPath(file.task_id, folders);
                const fullPath = folderPath.join('/') + '/' + (file.filename || fileName);
                setFilePath(fullPath);
              } else {
                setFilePath(file.task_id ? `${file.task_id}/${fileName}` : fileName);
              }

              // 檢查向量和圖譜數據狀態
              if (file.vector_count !== undefined && file.vector_count > 0) {
                setHasVectors(true);
                // 獲取向量詳細信息
                try {
                  const vectorResponse = await getFileVectors(fileId, 1, 0);
                  if (vectorResponse.success && vectorResponse.data) {
                    const vectorData = vectorResponse.data;
                    setVectorInfo({
                      chunkCount: vectorData.total || file.vector_count || file.chunk_count,
                      dimension: vectorData.stats?.dimension || (vectorData.vectors && vectorData.vectors.length > 0 && vectorData.vectors[0].vector ? vectorData.vectors[0].vector.length : undefined),
                    });
                  }
                } catch (error) {
                  console.error('Failed to load vector info:', error);
                }
              } else if (file.processing_status === 'completed' || file.status === 'processed') {
                setHasVectors(null);
              } else {
                setHasVectors(false);
              }

              if (file.kg_status === 'completed' || file.kg_status === 'extracted') {
                setHasGraph(true);
                // 獲取圖譜詳細信息
                try {
                  const graphResponse = await getFileGraph(fileId, 1, 0);
                  if (graphResponse.success && graphResponse.data) {
                    const graphData = graphResponse.data;
                    setGraphInfo({
                      nodeCount: graphData.stats?.node_count || graphData.total_nodes,
                      tripleCount: graphData.stats?.triple_count || graphData.total_triples || graphData.total,
                    });
                  }
                } catch (error) {
                  console.error('Failed to load graph info:', error);
                }
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
  }, [fileId, taskId, treeData, fileName]);

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

  // 修改時間：2025-12-08 12:00:00 UTC+8 - 移除 getCurrentPath，使用 filePath 狀態

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

              {/* 任務ID */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">任務ID</label>
                <div className="text-primary font-mono text-sm break-all">{fileTaskId || fileMetadata.task_id || '無'}</div>
              </div>

              {/* 路徑 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">路徑</label>
                <div className="text-primary break-words">{filePath || (fileMetadata.task_id ? `${fileMetadata.task_id}/${fileName}` : fileName)}</div>
              </div>

              {/* 文件類型 */}
              {fileMetadata.file_type && (
                <div>
                  <label className="text-sm font-medium text-tertiary block mb-1">文件類型</label>
                  <div className="text-primary">{fileMetadata.file_type}</div>
                </div>
              )}

              {/* 向量資料 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">向量</label>
                {hasVectors === true && vectorInfo ? (
                  <div className="space-y-1">
                    <div className="text-primary">
                      <span className="text-tertiary">塊數：</span>
                      {vectorInfo.chunkCount !== undefined ? vectorInfo.chunkCount : '無'}
                    </div>
                    <div className="text-primary">
                      <span className="text-tertiary">維度：</span>
                      {vectorInfo.dimension !== undefined ? vectorInfo.dimension : '無'}
                    </div>
                  </div>
                  ) : hasVectors === false ? (
                  <div className="text-tertiary">無</div>
                  ) : (
                  <div className="text-tertiary">載入中...</div>
                  )}
              </div>

              {/* 圖譜資料 */}
              <div>
                <label className="text-sm font-medium text-tertiary block mb-1">圖譜</label>
                {hasGraph === true && graphInfo ? (
                  <div className="space-y-1">
                    <div className="text-primary">
                      <span className="text-tertiary">節點數：</span>
                      {graphInfo.nodeCount !== undefined ? graphInfo.nodeCount : '無'}
                    </div>
                    <div className="text-primary">
                      <span className="text-tertiary">關係三元組：</span>
                      {graphInfo.tripleCount !== undefined ? graphInfo.tripleCount : '無'}
                    </div>
                  </div>
                  ) : hasGraph === false ? (
                  <div className="text-tertiary">無</div>
                  ) : (
                  <div className="text-tertiary">載入中...</div>
                  )}
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
