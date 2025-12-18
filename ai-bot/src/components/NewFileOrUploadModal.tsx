/**
 * 代碼功能說明: 新建空白 Markdown 檔案 Modal（只輸入檔名，建立 .md）
 * 創建日期: 2025-12-14 12:58:00 (UTC+8)
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-14 13:47:04 (UTC+8)
 */

import { useCallback, useMemo, useState } from 'react';
import { X } from 'lucide-react';

export interface NewFileOrUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  taskId: string | null;
  folderId?: string | null;
  folderLabel?: string | null;
  existingFilenames?: string[]; // 同目錄下已存在檔名（含草稿/後端已存在）
  containerKey?: string | null; // FileTree 的容器 key（workspace: {taskId}_workspace；資料夾: folder_id）
}

function normalizeMdFilename(input: string): string {
  const raw = String(input || '').trim();
  if (!raw) return 'untitled.md';
  if (raw.toLowerCase().endsWith('.md')) return raw;
  const noExt = raw.replace(/\.[^.]+$/, '');
  return `${noExt}.md`;
}

function makeUniqueUntitled(existingNames: Set<string>): string {
  const base = 'untitled.md';
  if (!existingNames.has(base.toLowerCase())) return base;
  for (let i = 1; i < 1000; i += 1) {
    const cand = `untitled(${i}).md`;
    if (!existingNames.has(cand.toLowerCase())) return cand;
  }
  // fallback（理論上不會到這裡）
  return `untitled(${Date.now()}).md`;
}

export default function NewFileOrUploadModal({
  isOpen,
  onClose,
  taskId,
  folderId = null,
  folderLabel = null,
  existingFilenames = [],
  containerKey = null,
}: NewFileOrUploadModalProps) {
  const [filename, setFilename] = useState<string>('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const locationLabel = useMemo(() => {
    if (!taskId) return '（請先選擇任務工作區/資料夾）';
    if (folderLabel) return `→ ${folderLabel}`;
    return '→ 任務工作區';
  }, [taskId, folderLabel]);

  const existingNameSet = useMemo(() => {
    const set = new Set<string>();
    (existingFilenames || []).forEach((n) => {
      const s = String(n || '').trim();
      if (s) set.add(s.toLowerCase());
    });
    return set;
  }, [existingFilenames]);

  const handleCreate = useCallback(async () => {
    if (!taskId) return;
    setCreating(true);
    setError(null);
    try {
      const raw = String(filename || '').trim();
      const finalName = raw ? normalizeMdFilename(raw) : makeUniqueUntitled(existingNameSet);
      // 修改時間：2025-12-14 13:28:13 (UTC+8)
      // 新增檔案先建立「本地草稿」，等到 /docs (preview-first) Apply 後才真正寫入後端
      const draftId = `draft-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const finalContainerKey = String(containerKey || folderId || `${taskId}_workspace`).trim();
      window.dispatchEvent(
        new CustomEvent('localDraftFileCreated', {
          detail: {
            taskId,
            folderId: folderId || null,
            containerKey: finalContainerKey,
            draftId,
            filename: finalName,
            createdAt: new Date().toISOString(),
          },
        })
      );

      onClose();
    } catch (e: any) {
      setError(e?.message || '創建失敗');
    } finally {
      setCreating(false);
    }
  }, [taskId, filename, folderId, onClose, existingNameSet, containerKey]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 theme-transition"
      onClick={onClose}
    >
      <div
        className="bg-secondary border border-primary rounded-lg shadow-xl w-full max-w-lg mx-4 overflow-hidden theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b border-primary theme-transition">
          <div>
            <h2 className="text-lg font-semibold text-primary theme-transition">
              新建檔案（Markdown）
            </h2>
            <div className="text-xs text-tertiary mt-1 theme-transition">
              {locationLabel}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-tertiary text-primary transition-colors theme-transition"
            aria-label="關閉"
            disabled={creating}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 space-y-3 theme-transition">
          {!taskId && (
            <div className="p-3 rounded border border-primary bg-tertiary text-primary text-sm theme-transition">
              請先在左側選擇任務工作區/資料夾後，再新建檔案。
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1 text-primary theme-transition">
              檔名（自動補 .md）
            </label>
            <input
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              className="w-full border border-primary rounded px-3 py-2 text-sm bg-secondary text-primary theme-transition"
              placeholder="untitled.md"
              disabled={creating}
            />
            <div className="text-xs text-tertiary mt-1 theme-transition">
              會先建立本地草稿檔，請到「文件助手」預覽 diff 後按 Apply 才會寫入後端。
            </div>
          </div>

          {error && <div className="text-sm text-red-400 theme-transition">{error}</div>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              className="px-4 py-2 rounded border border-primary hover:bg-tertiary text-primary transition-colors theme-transition"
              onClick={onClose}
              disabled={creating}
            >
              取消
            </button>
            <button
              className="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors theme-transition"
              onClick={handleCreate}
              disabled={!taskId || creating}
            >
              {creating ? '創建中…' : '創建'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
