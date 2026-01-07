/**
 * 代碼功能說明: 文件編輯狀態組件 - 顯示接受/拒絕/提交按鈕
 * 創建日期: 2026-01-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-06
 */

import { Check, X, Upload, Loader2 } from 'lucide-react';

interface FileEditStatusProps {
  /** 接受修改回調 */
  onAccept: () => void;
  /** 拒絕修改回調 */
  onReject: () => void;
  /** 提交修改回調 */
  onSubmit: () => void;
  /** 是否正在提交 */
  isSubmitting?: boolean;
}

/**
 * 文件編輯狀態組件
 *
 * 顯示三個操作按鈕：接受、拒絕、提交
 */
export default function FileEditStatus({
  onAccept,
  onReject,
  onSubmit,
  isSubmitting = false,
}: FileEditStatusProps) {
  return (
    <div className="flex items-center gap-2 ml-2">
      {/* 接受按鈕 */}
      <button
        onClick={onAccept}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg border border-green-500/50 transition-colors"
        title="接受修改"
        aria-label="接受修改"
      >
        <Check className="w-4 h-4" />
        <span>接受</span>
      </button>

      {/* 拒絕按鈕 */}
      <button
        onClick={onReject}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg border border-red-500/50 transition-colors"
        title="拒絕修改"
        aria-label="拒絕修改"
      >
        <X className="w-4 h-4" />
        <span>拒絕</span>
      </button>

      {/* 提交按鈕 */}
      <button
        onClick={onSubmit}
        disabled={isSubmitting}
        className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg border border-blue-500/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        title="提交修改到後端"
        aria-label="提交修改到後端"
      >
        {isSubmitting ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>提交中...</span>
          </>
        ) : (
          <>
            <Upload className="w-4 h-4" />
            <span>提交</span>
          </>
        )}
      </button>
    </div>
  );
}
