// 代碼功能說明: Review 相關類型定義
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

export interface DocumentVersion {
  version: number;
  version_file_id: string;
  storage_path: string;
  summary: string;
  request_id: string;
  created_at_ms?: number;
}

export interface ReviewState {
  originalContent: string;
  modifiedContent: string;
  currentChangeIndex: number;
  totalChanges: number;
}

export interface ChangeSummary {
  summary: string;
  addedLines?: number;
  removedLines?: number;
  modifiedChunks?: number;
}

