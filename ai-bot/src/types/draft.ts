// 代碼功能說明: Draft 和 Patch 類型定義
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

export interface Range {
  startLine: number;
  startColumn: number;
  endLine: number;
  endColumn: number;
}

export interface AIPatch {
  id: string;
  originalRange: Range;
  originalText: string;
  modifiedText: string;
  status: 'streaming' | 'pending_review' | 'accepted' | 'rejected';
  conflict: boolean;
}

export interface Heading {
  level: number;
  text: string;
  lineNumber: number;
  id?: string;
}
