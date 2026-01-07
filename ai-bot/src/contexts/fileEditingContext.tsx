/**
 * 代碼功能說明: 文件編輯 Context - 管理流式編輯狀態
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { createContext, useContext, useState, ReactNode, useMemo, useCallback, useEffect } from 'react';
import { SearchReplacePatch } from '../hooks/useStreamingEdit';

/**
 * 應用 Search-and-Replace patches 到內容
 * 性能優化：使用更高效的字符串替換算法，避免重複字符串操作
 */
function applyPatchesToContent(content: string, patches: SearchReplacePatch[]): string {
  if (!patches || patches.length === 0) {
    return content;
  }

  // 性能優化：大文件警告（> 5MB）
  const fileSizeMB = new Blob([content]).size / (1024 * 1024);
  if (fileSizeMB > 5) {
    console.warn(
      `Large file detected (${fileSizeMB.toFixed(2)} MB). Patch application may be slow.`
    );
  }

  // 性能優化：先計算所有匹配位置，然後從後往前應用，避免位置偏移
  const patchPositions: Array<{ patch: SearchReplacePatch; index: number }> = [];

  for (const patch of patches) {
    const index = content.indexOf(patch.search_block);
    if (index !== -1) {
      patchPositions.push({ patch, index });
    }
  }

  // 按位置降序排列（從後往前應用）
  patchPositions.sort((a, b) => b.index - a.index);

  // 性能優化：使用數組拼接而非字符串拼接，最後一次性轉換
  if (patchPositions.length === 0) {
    return content;
  }

  // 構建替換後的內容
  let result = '';
  let lastIndex = content.length;

  for (const { patch, index } of patchPositions) {
    // 添加當前 patch 之後的內容
    result = patch.replace_block + content.slice(index + patch.search_block.length, lastIndex) + result;
    lastIndex = index;
  }

  // 添加第一個 patch 之前的內容
  result = content.slice(0, lastIndex) + result;

  return result;
}

interface FileEditingContextValue {
  /** 當前編輯的文件 ID */
  editingFileId: string | null;
  /** 當前編輯的 patches */
  patches: SearchReplacePatch[];
  /** 原始文件內容 */
  originalContent: string | null;
  /** 應用 patches 後的修改內容 */
  modifiedContent: string | null;
  /** 當前編輯請求 ID */
  currentRequestId: string | null;
  /** 是否有未保存的修改 */
  hasUnsavedChanges: boolean;
  /** 設置編輯文件 */
  setEditingFile: (fileId: string | null) => void;
  /** 設置 patches */
  setPatches: (patches: SearchReplacePatch[]) => void;
  /** 設置原始內容 */
  setOriginalContent: (content: string) => void;
  /** 設置當前編輯請求 ID */
  setCurrentRequestId: (requestId: string | null) => void;
  /** 應用 patches 生成 modifiedContent */
  applyPatches: () => void;
  /** 接受修改（將 modifiedContent 設為 originalContent） */
  acceptChanges: () => void;
  /** 拒絕修改（恢復 originalContent） */
  rejectChanges: () => void;
  /** 清除編輯狀態 */
  clearEditing: () => void;
}

const FileEditingContext = createContext<FileEditingContextValue | undefined>(undefined);

export function FileEditingProvider({ children }: { children: ReactNode }) {
  const [editingFileId, setEditingFileId] = useState<string | null>(null);
  const [patches, setPatches] = useState<SearchReplacePatch[]>([]);
  const [originalContent, setOriginalContentState] = useState<string | null>(null);
  const [modifiedContent, setModifiedContent] = useState<string | null>(null);
  const [currentRequestId, setCurrentRequestIdState] = useState<string | null>(null);

  // 計算是否有未保存的修改
  const hasUnsavedChanges = useMemo(() => {
    if (!originalContent || !modifiedContent) {
      return false;
    }
    return originalContent !== modifiedContent;
  }, [originalContent, modifiedContent]);

  // 應用 patches 生成 modifiedContent
  const applyPatches = useCallback(() => {
    if (!originalContent || patches.length === 0) {
      setModifiedContent(null);
      return;
    }

    const appliedContent = applyPatchesToContent(originalContent, patches);
    setModifiedContent(appliedContent);
  }, [originalContent, patches]);

  // 當 patches 或 originalContent 變化時，自動應用 patches
  useEffect(() => {
    if (originalContent && patches.length > 0) {
      applyPatches();
    } else if (patches.length === 0) {
      // 如果沒有 patches，恢復到原始內容
      setModifiedContent(originalContent);
    }
  }, [patches, originalContent, applyPatches]);

  const setEditingFile = useCallback((fileId: string | null) => {
    setEditingFileId(fileId);
    if (!fileId) {
      setPatches([]);
      setOriginalContentState(null);
      setModifiedContent(null);
      setCurrentRequestIdState(null);
    }
  }, []);

  const setPatchesState = useCallback((newPatches: SearchReplacePatch[]) => {
    setPatches(newPatches);
  }, []);

  const setOriginalContent = useCallback((content: string) => {
    setOriginalContentState(content);
    // 重置修改內容
    setModifiedContent(null);
  }, []);

  const setCurrentRequestId = useCallback((requestId: string | null) => {
    setCurrentRequestIdState(requestId);
  }, []);

  const acceptChanges = useCallback(() => {
    if (modifiedContent) {
      // 將 modifiedContent 設為新的 originalContent
      setOriginalContentState(modifiedContent);
      // 清空 patches
      setPatches([]);
      // 重置 modifiedContent（因為 originalContent 已更新，會觸發 useEffect 重置）
      setModifiedContent(null);
    }
  }, [modifiedContent]);

  const rejectChanges = useCallback(() => {
    // 恢復到 originalContent
    setModifiedContent(originalContent);
    // 清空 patches
    setPatches([]);
  }, [originalContent]);

  const clearEditing = useCallback(() => {
    setEditingFileId(null);
    setPatches([]);
    setOriginalContentState(null);
    setModifiedContent(null);
    setCurrentRequestIdState(null);
  }, []);

  return (
    <FileEditingContext.Provider
      value={{
        editingFileId,
        patches,
        originalContent,
        modifiedContent,
        currentRequestId,
        hasUnsavedChanges,
        setEditingFile,
        setPatches: setPatchesState,
        setOriginalContent,
        setCurrentRequestId,
        applyPatches,
        acceptChanges,
        rejectChanges,
        clearEditing,
      }}
    >
      {children}
    </FileEditingContext.Provider>
  );
}

export function useFileEditing() {
  const context = useContext(FileEditingContext);
  if (!context) {
    throw new Error('useFileEditing must be used within FileEditingProvider');
  }
  return context;
}
