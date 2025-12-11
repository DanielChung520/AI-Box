/**
 * 代碼功能說明: 文件引用組件（類似 Cursor 中的文件引用）
 * 創建日期: 2025-12-08
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-08 10:40:00 UTC+8
 *
 * 功能說明:
 * - 顯示文件名稱
 * - 可刪除
 * - 包含隱藏的文件ID和路徑信息
 */

import React from 'react';
import { File as FileIcon, X } from 'lucide-react';

export interface FileReferenceData {
  fileId: string;
  fileName: string;
  filePath?: string; // 可選的文件路徑
  taskId?: string; // 可選的任務ID
}

interface FileReferenceProps {
  file: FileReferenceData;
  onRemove: (fileId: string) => void;
}

export default function FileReference({ file, onRemove }: FileReferenceProps) {
  return (
    <div
      className="inline-flex items-center gap-2 px-3 py-1.5 bg-blue-500/20 border border-blue-500/50 rounded-lg text-sm text-primary hover:bg-blue-500/30 transition-colors group"
      title={`文件ID: ${file.fileId}${file.filePath ? `\n路徑: ${file.filePath}` : ''}`}
    >
      <FileIcon className="w-4 h-4 text-blue-400 flex-shrink-0" />
      <span className="font-medium truncate max-w-[200px]">{file.fileName}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove(file.fileId);
        }}
        className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 hover:bg-blue-500/50 rounded text-tertiary hover:text-primary"
        aria-label="移除文件引用"
      >
        <X className="w-3 h-3" />
      </button>
      {/* 隱藏的文件ID和路徑信息（用於後續處理） */}
      <input type="hidden" name={`file_${file.fileId}_id`} value={file.fileId} />
      {file.filePath && (
        <input type="hidden" name={`file_${file.fileId}_path`} value={file.filePath} />
      )}
      {file.taskId && (
        <input type="hidden" name={`file_${file.fileId}_taskId`} value={file.taskId} />
      )}
    </div>
  );
}


