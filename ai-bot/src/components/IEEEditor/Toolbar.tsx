// 代碼功能說明: IEE 編輯器工具欄組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

import { Save, Eye, CheckCircle, Settings, SplitSquareHorizontal } from 'lucide-react';

interface ToolbarProps {
  onSave?: () => void;
  onReview?: () => void;
  onCommit?: () => void;
  onSettings?: () => void;
  isSaving?: boolean;
  hasUnsavedChanges?: boolean;
  showPreview?: boolean;
  onTogglePreview?: () => void;
}

export default function Toolbar({
  onSave,
  onReview,
  onCommit,
  onSettings,
  isSaving = false,
  hasUnsavedChanges = false,
  showPreview = false,
  onTogglePreview,
}: ToolbarProps) {
  return (
    <div className="flex items-center justify-between border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-2">
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          IEE 編輯器
        </h1>
      </div>
      <div className="flex items-center gap-2">
        {onTogglePreview && (
          <button
            onClick={onTogglePreview}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
              showPreview
                ? 'text-white bg-blue-600 hover:bg-blue-700'
                : 'text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
            title="切換預覽模式"
          >
            <SplitSquareHorizontal className="w-4 h-4" />
            預覽
          </button>
        )}
        <button
          onClick={onSave}
          disabled={isSaving || !hasUnsavedChanges}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed rounded-md transition-colors"
          title="保存文件 (Ctrl+S)"
        >
          <Save className="w-4 h-4" />
          {isSaving ? '保存中...' : '保存'}
        </button>
        <button
          onClick={onReview}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
          title="審查變更"
        >
          <Eye className="w-4 h-4" />
          審查
        </button>
        <button
          onClick={onCommit}
          disabled
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-md transition-colors"
          title="提交變更（預留接口）"
        >
          <CheckCircle className="w-4 h-4" />
          提交
        </button>
        <button
          onClick={onSettings}
          className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-md transition-colors"
          title="設置"
        >
          <Settings className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
