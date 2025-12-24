// 代碼功能說明: Markdown 工具函數
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import type { Heading } from '../types/draft';

/**
 * 解析 Markdown 標題結構
 * @param content - Markdown 內容
 * @returns 標題數組
 */
export function parseHeadings(content: string): Heading[] {
  const headings: Heading[] = [];
  const lines = content.split('\n');

  lines.forEach((line, index) => {
    // 匹配 Markdown 標題（# 開頭）
    const match = line.match(/^(#{1,6})\s+(.+)$/);
    if (match) {
      const level = match[1].length;
      const text = match[2].trim();
      headings.push({
        level,
        text,
        lineNumber: index + 1, // Monaco Editor 使用 1-based 行號
        id: `heading-${headings.length}`,
      });
    }
  });

  return headings;
}
