// 代碼功能說明: 變更點導航組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useEffect, useState } from 'react';
import { ChevronUp, ChevronDown } from 'lucide-react';
import type { editor } from 'monaco-editor';

export interface ChangeNavigationProps {
  diffEditor: editor.IStandaloneDiffEditor | null;
  currentIndex: number;
  totalChanges: number;
  onIndexChange?: (index: number) => void;
}

interface DiffNavigator {
  canNavigate: () => boolean;
  next: () => boolean;
  previous: () => boolean;
}

export default function ChangeNavigation({
  diffEditor,
  currentIndex,
  totalChanges,
  onIndexChange,
}: ChangeNavigationProps) {
  const [navigator, setNavigator] = useState<DiffNavigator | null>(null);

  useEffect(() => {
    if (!diffEditor) {
      setNavigator(null);
      return;
    }

    // 創建 Diff Navigator
    const nav = diffEditor.getLineChanges() || [];
    const navigatorInstance = {
      canNavigate: () => nav.length > 0,
      next: () => {
        const changes = diffEditor.getLineChanges();
        if (!changes || changes.length === 0) return false;

        const nextIndex = currentIndex < changes.length - 1 ? currentIndex + 1 : 0;
        const change = changes[nextIndex];

        if (change) {
          const modifiedEditor = diffEditor.getModifiedEditor();
          modifiedEditor.revealLineInCenter(change.modifiedStartLineNumber);
          modifiedEditor.setPosition({
            lineNumber: change.modifiedStartLineNumber,
            column: 1,
          });
          modifiedEditor.focus();

          if (onIndexChange) {
            onIndexChange(nextIndex);
          }
          return true;
        }
        return false;
      },
      previous: () => {
        const changes = diffEditor.getLineChanges();
        if (!changes || changes.length === 0) return false;

        const prevIndex = currentIndex > 0 ? currentIndex - 1 : changes.length - 1;
        const change = changes[prevIndex];

        if (change) {
          const modifiedEditor = diffEditor.getModifiedEditor();
          modifiedEditor.revealLineInCenter(change.modifiedStartLineNumber);
          modifiedEditor.setPosition({
            lineNumber: change.modifiedStartLineNumber,
            column: 1,
          });
          modifiedEditor.focus();

          if (onIndexChange) {
            onIndexChange(prevIndex);
          }
          return true;
        }
        return false;
      },
    };

    setNavigator(navigatorInstance);
  }, [diffEditor, currentIndex, onIndexChange]);

  const handlePrevious = () => {
    if (navigator && navigator.previous) {
      navigator.previous();
    }
  };

  const handleNext = () => {
    if (navigator && navigator.next) {
      navigator.next();
    }
  };

  if (totalChanges === 0) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
      <button
        onClick={handlePrevious}
        disabled={!navigator || totalChanges === 0}
        className="flex items-center gap-1 px-2 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded border border-gray-300 dark:border-gray-600 transition-colors"
        title="上一個變更"
      >
        <ChevronUp className="w-4 h-4" />
        上一個
      </button>
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {currentIndex + 1} / {totalChanges}
      </span>
      <button
        onClick={handleNext}
        disabled={!navigator || totalChanges === 0}
        className="flex items-center gap-1 px-2 py-1 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded border border-gray-300 dark:border-gray-600 transition-colors"
        title="下一個變更"
      >
        下一個
        <ChevronDown className="w-4 h-4" />
      </button>
    </div>
  );
}
