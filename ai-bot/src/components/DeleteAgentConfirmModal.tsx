// 代碼功能說明: 刪除代理確認模態框組件
// 創建日期: 2026-01-13
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-13

/**
 * 刪除代理確認模態框
 * 要求用戶輸入 "DELETE" 才能刪除代理
 */

import { useState } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';

interface DeleteAgentConfirmModalProps {
  isOpen: boolean;
  agentId: string;
  agentName: string;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

const CONFIRM_TEXT = 'DELETE';

export default function DeleteAgentConfirmModal({
  isOpen,
  agentId,
  agentName,
  onClose,
  onConfirm,
}: DeleteAgentConfirmModalProps) {
  const { t } = useLanguage();
  const [confirmInput, setConfirmInput] = useState('');
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canDelete = confirmInput === CONFIRM_TEXT && !isDeleting;

  const handleClose = () => {
    if (!isDeleting) {
      setConfirmInput('');
      setError(null);
      onClose();
    }
  };

  const handleDelete = async () => {
    if (!canDelete) return;

    setIsDeleting(true);
    setError(null);

    try {
      await onConfirm();
      // 成功後重置並關閉
      setConfirmInput('');
      setError(null);
      onClose();
    } catch (err: any) {
      setError(err.message || t('agentConfig.errors.deleteFailed', '刪除失敗，請稍後再試'));
    } finally {
      setIsDeleting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition"
      onClick={handleClose}
    >
      <div
        className={cn(
          "bg-secondary border border-primary rounded-lg shadow-xl max-w-md w-full mx-4 theme-transition"
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 模態框頭部 */}
        <div className="p-4 border-b border-primary flex items-center justify-between bg-red-500/10">
          <div className="flex items-center">
            <i className="fa-solid fa-exclamation-triangle mr-3 text-red-400"></i>
            <h3 className="text-lg font-semibold text-primary">
              {t('agentConfig.delete.title', '確認刪除代理')}
            </h3>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-full hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            disabled={isDeleting}
            aria-label={t('modal.close', '關閉')}
          >
            <i className="fa-solid fa-times"></i>
          </button>
        </div>

        {/* 模態框內容 */}
        <div className="p-6 space-y-4">
          {/* 警告信息 */}
          <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-lg">
            <p className="text-sm text-red-400 mb-2">
              <i className="fa-solid fa-exclamation-circle mr-2"></i>
              {t('agentConfig.delete.warning', '此操作無法撤銷！')}
            </p>
            <p className="text-sm text-primary">
              {t('agentConfig.delete.message', '您即將刪除代理')}：
            </p>
            <p className="text-sm font-medium text-primary mt-1">
              <span className="text-red-400">{agentName}</span>
              <span className="text-tertiary ml-2">({agentId})</span>
            </p>
          </div>

          {/* 確認輸入 */}
          <div>
            <label className="block text-sm font-medium text-primary mb-2">
              {t('agentConfig.delete.confirmLabel', '請輸入 "DELETE" 以確認刪除')}：
            </label>
            <input
              type="text"
              value={confirmInput}
              onChange={(e) => {
                setConfirmInput(e.target.value);
                setError(null);
              }}
              className={cn(
                "w-full px-4 py-2 bg-tertiary border rounded-lg text-primary focus:outline-none focus:ring-2",
                confirmInput === CONFIRM_TEXT
                  ? "border-green-500 focus:ring-green-500"
                  : "border-primary focus:ring-blue-500"
              )}
              placeholder={CONFIRM_TEXT}
              disabled={isDeleting}
              autoFocus
            />
            <p className="text-xs text-tertiary mt-1">
              {t('agentConfig.delete.hint', '輸入 "DELETE" 後，刪除按鈕將變為可用')}
            </p>
          </div>

          {/* 錯誤信息 */}
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
              <i className="fa-solid fa-exclamation-circle mr-2"></i>
              {error}
            </div>
          )}
        </div>

        {/* 模態框底部 */}
        <div className="p-4 border-t border-primary flex justify-end gap-3 bg-tertiary/20">
          <button
            onClick={handleClose}
            className="px-4 py-2 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
            disabled={isDeleting}
          >
            {t('modal.cancel', '取消')}
          </button>
          <button
            onClick={handleDelete}
            className={cn(
              "px-6 py-2 rounded-lg text-white transition-colors flex items-center",
              canDelete
                ? "bg-red-600 hover:bg-red-700"
                : "bg-gray-500 cursor-not-allowed opacity-50"
            )}
            disabled={!canDelete}
          >
            {isDeleting ? (
              <>
                <i className="fa-solid fa-spinner fa-spin mr-2"></i>
                {t('agentConfig.delete.deleting', '刪除中...')}
              </>
            ) : (
              <>
                <i className="fa-solid fa-trash mr-2"></i>
                {t('agentConfig.delete.confirm', '確認刪除')}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
