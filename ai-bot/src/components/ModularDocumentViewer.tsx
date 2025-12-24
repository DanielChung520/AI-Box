/**
 * 代碼功能說明: 模組化文檔虛擬合併預覽組件
 * 創建日期: 2025-12-20
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-20
 */

import { useState, useEffect, useCallback } from 'react';
import { parseTransclusionSyntax, mergeDocumentContent, type TransclusionReference } from '../utils/modularDocument';
import { previewFile } from '../lib/api';
import MarkdownViewer from './MarkdownViewer';

interface ModularDocumentViewerProps {
  /** 主文檔內容 */
  content: string;
  /** 任務 ID（用於查找文件） */
  taskId?: string;
  /** 是否顯示加載狀態 */
  showLoading?: boolean;
  /** 加載錯誤處理 */
  onError?: (error: Error) => void;
}

/**
 * 模組化文檔虛擬合併預覽組件
 * 用於在主文檔中顯示分文檔內容，實現無縫滾動體驗
 */
export default function ModularDocumentViewer({
  content,
  taskId,
  showLoading = true,
  onError,
}: ModularDocumentViewerProps) {
  const [mergedContent, setMergedContent] = useState<string>(content);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [references, setReferences] = useState<TransclusionReference[]>([]);
  const [loadedFiles, setLoadedFiles] = useState<Map<string, string>>(new Map());
  const [failedFiles, setFailedFiles] = useState<string[]>([]);

  /**
   * 加載分文檔內容
   */
  const loadSubDocuments = useCallback(async () => {
    // 解析 Transclusion 語法
    const refs = parseTransclusionSyntax(content);
    setReferences(refs);

    if (refs.length === 0) {
      // 沒有引用，直接使用原始內容
      setMergedContent(content);
      return;
    }

    setIsLoading(true);
    setFailedFiles([]);

    try {
      // 去重文件列表
      const uniqueFilenames = Array.from(new Set(refs.map((ref) => ref.filename)));

      // 並行加載所有文件
      const loaded = new Map<string, string>();
      const failed: string[] = [];

      const loadPromises = uniqueFilenames.map(async (filename) => {
        try {
          // 使用文件查找 API 查找文件
          const lookupResponse = await fetch(
            `/api/v1/files/lookup/exact?filename=${encodeURIComponent(filename)}&task_id=${encodeURIComponent(taskId!)}`,
            {
              method: 'GET',
              headers: {
                'Content-Type': 'application/json',
              },
              credentials: 'include',
            }
          );

          if (!lookupResponse.ok) {
            throw new Error(`Failed to lookup file: ${filename}`);
          }

          const lookupData = await lookupResponse.json();
          if (!lookupData.success || !lookupData.data) {
            throw new Error(`File not found: ${filename}`);
          }

          const fileId = lookupData.data.file_id;

          // 使用 previewFile API 加載文件內容
          const preview = await previewFile(fileId);
          if (preview.success && preview.data?.content) {
            loaded.set(filename, preview.data.content);
          } else {
            throw new Error(`Failed to load file content: ${filename}`);
          }
        } catch (error) {
          console.error(`Failed to load sub-document: ${filename}`, error);
          failed.push(filename);
        }
      });

      await Promise.all(loadPromises);

      setLoadedFiles(loaded);
      setFailedFiles(failed);

      // 合併內容
      const merged = mergeDocumentContent(content, loaded, refs);
      setMergedContent(merged);
    } catch (error) {
      console.error('Failed to load sub-documents:', error);
      if (onError && error instanceof Error) {
        onError(error);
      }
      // 如果加載失敗，顯示原始內容
      setMergedContent(content);
    } finally {
      setIsLoading(false);
    }
  }, [content, taskId, onError]);

  // 當內容或任務 ID 變化時，重新加載
  useEffect(() => {
    loadSubDocuments();
  }, [loadSubDocuments]);

  // 顯示加載狀態
  if (showLoading && isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-sm text-gray-500">正在加載分文檔...</div>
      </div>
    );
  }

  // 顯示錯誤信息（如果有文件加載失敗）
  const hasErrors = failedFiles.length > 0;

  return (
    <div className="modular-document-viewer">
      {hasErrors && (
        <div className="mb-4 rounded-lg bg-yellow-50 border border-yellow-200 p-4">
          <div className="text-sm font-medium text-yellow-800">
            部分分文檔無法加載
          </div>
          <ul className="mt-2 text-sm text-yellow-700 list-disc list-inside">
            {failedFiles.map((filename) => (
              <li key={filename}>{filename}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 顯示合併後的內容 */}
      <MarkdownViewer content={mergedContent} />
    </div>
  );
}
