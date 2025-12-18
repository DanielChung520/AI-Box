/**
 * 代碼功能說明: 檔案編輯預覽 Modal（顯示 diff 並提供 Apply 按鈕）
 * 創建日期: 2025-12-14 14:30:00 (UTC+8)
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-14 14:30:00 (UTC+8)
 */

import { useState, useEffect } from 'react';
import { X, Check, Loader2 } from 'lucide-react';
import { getDocEditState, applyDocEdit } from '../lib/api';

export interface FileEditPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  fileId: string;
  filename: string;
  requestId: string;
  taskId: string;
  onApplied?: () => void;
}

export default function FileEditPreviewModal({
  isOpen,
  onClose,
  fileId,
  filename,
  requestId,
  taskId,
  onApplied,
}: FileEditPreviewModalProps) {
  const [preview, setPreview] = useState<any>(null);
  const [status, setStatus] = useState<string>('queued');
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 輪詢預覽狀態
  useEffect(() => {
    if (!isOpen || !requestId) return;

    let cancelled = false;
    const pollStatus = async () => {
      const maxAttempts = 60; // 最多輪詢 30 秒
      for (let i = 0; i < maxAttempts; i++) {
        if (cancelled) return;
        try {
          const resp = await getDocEditState(requestId);
          const currentStatus = (resp as any)?.data?.status;
          setStatus(currentStatus);

          if (currentStatus === 'succeeded') {
            const previewData = (resp as any)?.data?.preview;
            setPreview(previewData);
            setLoading(false);
            break;
          } else if (currentStatus === 'failed' || currentStatus === 'aborted') {
            const errorMsg = (resp as any)?.data?.error_message || '編輯預覽失敗';
            setError(errorMsg);
            setLoading(false);
            break;
          }

          await new Promise((r) => setTimeout(r, 500));
        } catch (e: any) {
          if (cancelled) return;
          setError(e?.message || '獲取預覽狀態失敗');
          setLoading(false);
          break;
        }
      }
    };

    setLoading(true);
    setError(null);
    setPreview(null);
    pollStatus();

    return () => {
      cancelled = true;
    };
  }, [isOpen, requestId]);

  const handleApply = async () => {
    if (!requestId) return;
    setApplying(true);
    setError(null);
    try {
      const resp = await applyDocEdit(requestId);
      if (resp?.success) {
        // 觸發檔案更新事件
        window.dispatchEvent(
          new CustomEvent('fileUploaded', {
            detail: {
              taskId,
              fileIds: [fileId],
            },
          })
        );
        onApplied?.();
        onClose();
      } else {
        setError((resp as any)?.message || 'Apply 失敗');
      }
    } catch (e: any) {
      setError(e?.message || 'Apply 失敗');
    } finally {
      setApplying(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[70] flex items-center justify-center bg-black/50 theme-transition"
      onClick={onClose}
    >
      <div
        className="bg-secondary border border-primary rounded-lg shadow-xl w-full max-w-4xl mx-4 max-h-[90vh] overflow-hidden flex flex-col theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-primary theme-transition">
          <div>
            <h2 className="text-lg font-semibold text-primary theme-transition">
              檔案編輯預覽
            </h2>
            <div className="text-xs text-tertiary mt-1 theme-transition">
              {filename}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-tertiary text-primary transition-colors theme-transition"
            aria-label="關閉"
            disabled={applying}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4 theme-transition">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
              <span className="ml-2 text-primary theme-transition">正在生成預覽...</span>
            </div>
          )}

          {error && (
            <div className="p-3 rounded border border-red-500/30 bg-red-500/10 text-red-400 text-sm theme-transition">
              {error}
            </div>
          )}

          {status && !loading && !error && (
            <div className="text-sm text-tertiary theme-transition">
              狀態：{status === 'queued' ? '排隊中' : status === 'running' ? '處理中' : status === 'succeeded' ? '完成' : status}
            </div>
          )}

          {preview && (
            <div className="space-y-4">
              {preview.summary && (
                <div className="p-3 rounded border border-primary bg-tertiary text-primary text-sm theme-transition">
                  <div className="font-medium mb-1">變更摘要</div>
                  <div>{preview.summary}</div>
                </div>
              )}

              <div className="border rounded-lg bg-white dark:bg-gray-800 p-4 theme-transition">
                <div className="font-medium mb-2 text-primary theme-transition">Patch Preview</div>
                {preview.patch_kind === 'json_patch' ? (
                  <pre className="text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 border rounded p-2 max-h-[400px] overflow-auto text-primary theme-transition">
                    {JSON.stringify(preview.patch, null, 2)}
                  </pre>
                ) : (
                  <pre className="text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 border rounded p-2 max-h-[400px] overflow-auto text-primary theme-transition">
                    {String(preview.patch || '')}
                  </pre>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 p-4 border-t border-primary theme-transition">
          <button
            className="px-4 py-2 rounded border border-primary hover:bg-tertiary text-primary transition-colors theme-transition"
            onClick={onClose}
            disabled={applying}
          >
            取消
          </button>
          <button
            className="px-4 py-2 rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors theme-transition flex items-center gap-2"
            onClick={handleApply}
            disabled={applying || !preview || status !== 'succeeded'}
          >
            {applying ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                套用中...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Apply
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
