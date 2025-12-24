// 代碼功能說明: Markdown 工具函數測試
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { describe, it, expect } from 'vitest';
import { parseHeadings } from '../../../src/utils/markdown';

describe('parseHeadings', () => {
  it('應該解析單個 H1 標題', () => {
    const content = '# 標題 1\n\n這是內容';
    const headings = parseHeadings(content);

    expect(headings).toHaveLength(1);
    expect(headings[0]).toEqual({
      level: 1,
      text: '標題 1',
      lineNumber: 1,
      id: 'heading-0',
    });
  });

  it('應該解析多個不同層級的標題', () => {
    const content = `# 標題 1
內容
## 標題 2
更多內容
### 標題 3
細節內容`;
    const headings = parseHeadings(content);

    expect(headings).toHaveLength(3);
    expect(headings[0].level).toBe(1);
    expect(headings[1].level).toBe(2);
    expect(headings[2].level).toBe(3);
  });

  it('應該正確計算行號', () => {
    const content = `第一行
第二行
# 標題在第 3 行
第四行
## 標題在第 5 行`;
    const headings = parseHeadings(content);

    expect(headings[0].lineNumber).toBe(3);
    expect(headings[1].lineNumber).toBe(5);
  });

  it('應該處理沒有標題的內容', () => {
    const content = '這是一段沒有標題的內容';
    const headings = parseHeadings(content);

    expect(headings).toHaveLength(0);
  });

  it('應該處理空內容', () => {
    const content = '';
    const headings = parseHeadings(content);

    expect(headings).toHaveLength(0);
  });
});
