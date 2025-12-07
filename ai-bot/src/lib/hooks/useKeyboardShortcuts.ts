/**
 * 代碼功能說明: 全局快捷鍵 Hook
 * 創建日期: 2025-12-07
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-07
 *
 * 功能說明:
 * - 實現全局快捷鍵監聽
 * - Cmd/Ctrl + P: 打開搜尋檔案對話框
 * - Esc: 關閉當前對話框或取消操作
 */

import { useEffect, useCallback } from 'react';

interface UseKeyboardShortcutsOptions {
  onSearch?: () => void;
  onEscape?: () => void;
  enabled?: boolean;
}

export function useKeyboardShortcuts({
  onSearch,
  onEscape,
  enabled = true,
}: UseKeyboardShortcutsOptions = {}) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // 檢查是否在輸入框中（不響應快捷鍵）
      const target = e.target as HTMLElement;
      const isInputFocused =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Cmd/Ctrl + P: 打開搜尋檔案對話框
      if ((e.metaKey || e.ctrlKey) && e.key === 'p' && !isInputFocused) {
        e.preventDefault();
        if (onSearch) {
          onSearch();
        }
      }

      // Esc: 關閉當前對話框或取消操作
      if (e.key === 'Escape' && !isInputFocused) {
        if (onEscape) {
          onEscape();
        }
      }
    },
    [onSearch, onEscape]
  );

  useEffect(() => {
    if (!enabled) return;

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, enabled]);
}
