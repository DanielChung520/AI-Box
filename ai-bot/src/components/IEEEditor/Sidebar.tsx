// 代碼功能說明: IEE 編輯器側邊欄組件（大綱導航）
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { useEffect, useState } from 'react';
import type { Heading } from '../../types/draft';
import { parseHeadings } from '../../utils/markdown';
import type { editor } from 'monaco-editor';

interface SidebarProps {
  content: string;
  editor?: editor.IStandaloneCodeEditor | null;
  currentLine?: number;
}

export default function Sidebar({ content, editor, currentLine }: SidebarProps) {
  const [headings, setHeadings] = useState<Heading[]>([]);

  useEffect(() => {
    const parsed = parseHeadings(content);
    setHeadings(parsed);
  }, [content]);

  const handleHeadingClick = (lineNumber: number) => {
    if (editor) {
      editor.revealLineInCenter(lineNumber);
      editor.setPosition({ lineNumber, column: 1 });
      editor.focus();
    }
  };

  const renderHeading = (heading: Heading, index: number) => {
    const isActive = currentLine !== undefined && heading.lineNumber === currentLine;
    const indent = (heading.level - 1) * 16;

    return (
      <div
        key={heading.id || index}
        className={`cursor-pointer py-1 px-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors ${
          isActive
            ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 font-medium'
            : 'text-gray-700 dark:text-gray-300'
        }`}
        style={{ paddingLeft: `${8 + indent}px` }}
        onClick={() => handleHeadingClick(heading.lineNumber)}
        title={`跳轉到第 ${heading.lineNumber} 行`}
      >
        <span className="text-gray-500 dark:text-gray-400 mr-2">
          {'#'.repeat(heading.level)}
        </span>
        {heading.text}
      </div>
    );
  };

  return (
    <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 h-full overflow-y-auto">
      <div className="p-4">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
          大綱
        </h2>
        {headings.length === 0 ? (
          <p className="text-xs text-gray-500 dark:text-gray-400">
            沒有標題
          </p>
        ) : (
          <div className="space-y-1">{headings.map(renderHeading)}</div>
        )}
      </div>
    </div>
  );
}
