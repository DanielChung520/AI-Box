// 代碼功能說明: 文件操作狀態管理（剪貼板、批量選擇、文件樹緩存、聚焦狀態）
// 創建日期: 2025-12-07
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-07

/**
 * 文件操作狀態管理模組
 * 提供剪貼板狀態管理、批量選擇、文件樹狀態緩存、聚焦狀態管理等功能
 */

// ==================== 類型定義 ====================

export interface ClipboardItem {
  id: string;
  type: 'file' | 'folder';
  name: string;
}

export interface ClipboardState {
  type: 'cut' | 'copy';
  items: ClipboardItem[];
  timestamp: number;
}

export interface FileTreeCache {
  tree: Record<string, any[]>;
  timestamp: number;
  expiresIn: number; // 緩存過期時間（毫秒）
}

// ==================== 剪貼板狀態管理 ====================

const CLIPBOARD_STORAGE_KEY = 'file_clipboard_state';

/**
 * 保存剪貼板狀態到 localStorage
 */
export function saveClipboardState(state: ClipboardState): void {
  try {
    localStorage.setItem(CLIPBOARD_STORAGE_KEY, JSON.stringify(state));
  } catch (error) {
    console.error('Failed to save clipboard state:', error);
  }
}

/**
 * 讀取剪貼板狀態從 localStorage
 */
export function loadClipboardState(): ClipboardState | null {
  try {
    const saved = localStorage.getItem(CLIPBOARD_STORAGE_KEY);
    if (!saved) return null;
    return JSON.parse(saved) as ClipboardState;
  } catch (error) {
    console.error('Failed to load clipboard state:', error);
    return null;
  }
}

/**
 * 清除剪貼板狀態
 */
export function clearClipboardState(): void {
  try {
    localStorage.removeItem(CLIPBOARD_STORAGE_KEY);
  } catch (error) {
    console.error('Failed to clear clipboard state:', error);
  }
}

/**
 * 檢查剪貼板是否為空
 */
export function isClipboardEmpty(): boolean {
  const state = loadClipboardState();
  return !state || state.items.length === 0;
}

// ==================== 文件樹狀態緩存 ====================

const FILE_TREE_CACHE_KEY_PREFIX = 'file_tree_cache_';
const DEFAULT_CACHE_EXPIRES_IN = 5 * 60 * 1000; // 5分鐘

/**
 * 生成文件樹緩存的鍵
 */
function getFileTreeCacheKey(userId?: string, taskId?: string): string {
  const key = `${FILE_TREE_CACHE_KEY_PREFIX}${userId || 'default'}_${taskId || 'all'}`;
  return key;
}

/**
 * 保存文件樹狀態到 localStorage
 */
export function saveFileTreeCache(
  tree: Record<string, any[]>,
  userId?: string,
  taskId?: string,
  expiresIn: number = DEFAULT_CACHE_EXPIRES_IN
): void {
  try {
    const cache: FileTreeCache = {
      tree,
      timestamp: Date.now(),
      expiresIn,
    };
    const key = getFileTreeCacheKey(userId, taskId);
    localStorage.setItem(key, JSON.stringify(cache));
  } catch (error) {
    console.error('Failed to save file tree cache:', error);
  }
}

/**
 * 讀取文件樹狀態從 localStorage
 */
export function loadFileTreeCache(
  userId?: string,
  taskId?: string
): Record<string, any[]> | null {
  try {
    const key = getFileTreeCacheKey(userId, taskId);
    const saved = localStorage.getItem(key);
    if (!saved) return null;

    const cache = JSON.parse(saved) as FileTreeCache;
    const now = Date.now();

    // 檢查是否過期
    if (now - cache.timestamp > cache.expiresIn) {
      localStorage.removeItem(key);
      return null;
    }

    return cache.tree;
  } catch (error) {
    console.error('Failed to load file tree cache:', error);
    return null;
  }
}

/**
 * 清除文件樹緩存
 */
export function clearFileTreeCache(userId?: string, taskId?: string): void {
  try {
    const key = getFileTreeCacheKey(userId, taskId);
    localStorage.removeItem(key);
  } catch (error) {
    console.error('Failed to clear file tree cache:', error);
  }
}

/**
 * 清除所有文件樹緩存
 */
export function clearAllFileTreeCache(): void {
  try {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith(FILE_TREE_CACHE_KEY_PREFIX)) {
        localStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.error('Failed to clear all file tree cache:', error);
  }
}

// ==================== React Hooks ====================

import { useState, useEffect, useCallback } from 'react';

/**
 * 批量選擇狀態管理 Hook
 */
export function useBatchSelection() {
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());

  const toggleSelection = useCallback((id: string) => {
    setSelectedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  }, []);

  const selectItem = useCallback((id: string) => {
    setSelectedItems((prev) => new Set(prev).add(id));
  }, []);

  const deselectItem = useCallback((id: string) => {
    setSelectedItems((prev) => {
      const newSet = new Set(prev);
      newSet.delete(id);
      return newSet;
    });
  }, []);

  const selectAll = useCallback((ids: string[]) => {
    setSelectedItems(new Set(ids));
  }, []);

  const deselectAll = useCallback(() => {
    setSelectedItems(new Set());
  }, []);

  const isSelected = useCallback(
    (id: string) => selectedItems.has(id),
    [selectedItems]
  );

  const getSelectedCount = useCallback(() => selectedItems.size, [selectedItems]);

  return {
    selectedItems,
    toggleSelection,
    selectItem,
    deselectItem,
    selectAll,
    deselectAll,
    isSelected,
    getSelectedCount,
  };
}

/**
 * 聚焦狀態管理 Hook
 */
export function useFocusState() {
  const [focusedItemId, setFocusedItemId] = useState<string | null>(null);

  const setFocus = useCallback((id: string | null) => {
    setFocusedItemId(id);
  }, []);

  const clearFocus = useCallback(() => {
    setFocusedItemId(null);
  }, []);

  const isFocused = useCallback(
    (id: string) => focusedItemId === id,
    [focusedItemId]
  );

  return {
    focusedItemId,
    setFocus,
    clearFocus,
    isFocused,
  };
}

/**
 * 剪貼板狀態管理 Hook
 */
export function useClipboardState() {
  const [clipboardState, setClipboardState] = useState<ClipboardState | null>(
    null
  );

  useEffect(() => {
    // 初始化時從 localStorage 讀取
    const saved = loadClipboardState();
    setClipboardState(saved);
  }, []);

  const setClipboard = useCallback((state: ClipboardState) => {
    saveClipboardState(state);
    setClipboardState(state);
  }, []);

  const clearClipboard = useCallback(() => {
    clearClipboardState();
    setClipboardState(null);
  }, []);

  const cutItems = useCallback((items: ClipboardItem[]) => {
    const state: ClipboardState = {
      type: 'cut',
      items,
      timestamp: Date.now(),
    };
    setClipboard(state);
  }, [setClipboard]);

  const copyItems = useCallback((items: ClipboardItem[]) => {
    const state: ClipboardState = {
      type: 'copy',
      items,
      timestamp: Date.now(),
    };
    setClipboard(state);
  }, [setClipboard]);

  return {
    clipboardState,
    setClipboard,
    clearClipboard,
    cutItems,
    copyItems,
    isEmpty: !clipboardState || clipboardState.items.length === 0,
  };
}
