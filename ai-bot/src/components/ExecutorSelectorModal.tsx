/**
 * 执行者选择模态框组件
 * 功能：当用户点击收藏的助理或代理时，弹出选择界面
 * 创建日期：2025-01-27
 * 创建人：Daniel Chung
 * 最后修改日期：2025-01-27
 */

import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';

interface ExecutorSelectorModalProps {
  isOpen: boolean;
  type: 'assistant' | 'agent';
  executorId: string;
  executorName: string;
  executorDescription?: string;
  hasCurrentTask: boolean;
  onClose: () => void;
  onCreateTask: () => void;
  onApplyToCurrent: () => void;
}

export default function ExecutorSelectorModal({
  isOpen,
  type,
  executorId,
  executorName,
  executorDescription,
  hasCurrentTask,
  onClose,
  onCreateTask,
  onApplyToCurrent,
}: ExecutorSelectorModalProps) {
  const { t } = useLanguage();

  if (!isOpen) return null;

  const isAssistant = type === 'assistant';
  const icon = isAssistant ? 'fa-robot' : 'fa-user-tie';
  const colorClass = isAssistant ? 'text-purple-400' : 'text-green-400';
  const bgColorClass = isAssistant ? 'bg-purple-500/10' : 'bg-green-500/10';
  const borderColorClass = isAssistant ? 'border-purple-500/20' : 'border-green-500/20';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition"
      onClick={onClose}
    >
      <div
        className={cn(
          "bg-secondary border border-primary rounded-lg shadow-xl max-w-md w-full mx-4 theme-transition",
          borderColorClass
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 模态框头部 */}
        <div className={cn("p-4 border-b border-primary flex items-center", bgColorClass)}>
          <i className={cn(`fa-solid ${icon} mr-3`, colorClass)}></i>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-primary">
              {isAssistant ? t('modal.selectAssistant') : t('modal.selectAgent')}
            </h3>
            <p className="text-sm text-tertiary mt-1">{executorName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label={t('modal.close')}
          >
            <i className="fa-solid fa-times"></i>
          </button>
        </div>

        {/* 模态框内容 */}
        <div className="p-4">
          {executorDescription && (
            <div className="mb-4">
              <p className="text-sm text-secondary">{executorDescription}</p>
            </div>
          )}

          {/* 选择选项 */}
          <div className="space-y-3">
            <button
              onClick={onCreateTask}
              className="w-full p-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center justify-center"
            >
              <i className="fa-solid fa-plus-circle mr-2"></i>
              <span>{t('modal.createNewTask')}</span>
            </button>

            {hasCurrentTask && (
              <button
                onClick={onApplyToCurrent}
                className="w-full p-3 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors flex items-center justify-center"
              >
                <i className="fa-solid fa-link mr-2"></i>
                <span>{t('modal.applyToCurrentTask')}</span>
              </button>
            )}
          </div>
        </div>

        {/* 模态框底部 */}
        <div className="p-4 border-t border-primary flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-tertiary hover:bg-hover text-primary transition-colors"
          >
            {t('modal.cancel')}
          </button>
        </div>
      </div>
    </div>
  );
}
