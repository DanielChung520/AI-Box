// 代碼功能說明: IEE 編輯器狀態欄組件
// 創建日期: 2025-12-20
// 創建人: Daniel Chung
// 最後修改日期: 2025-12-20

interface StatusBarProps {
  fileName?: string;
  filePath?: string;
  isSaved?: boolean;
  isSaving?: boolean;
  cursorLine?: number;
  cursorColumn?: number;
  totalLines?: number;
  totalChars?: number;
}

export default function StatusBar({
  fileName,
  filePath,
  isSaved = true,
  isSaving = false,
  cursorLine,
  cursorColumn,
  totalLines,
  totalChars,
}: StatusBarProps) {
  const getStatusText = () => {
    if (isSaving) return '保存中...';
    if (isSaved) return '已保存';
    return '未保存';
  };

  const getStatusColor = () => {
    if (isSaving) return 'text-yellow-600 dark:text-yellow-400';
    if (isSaved) return 'text-green-600 dark:text-green-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <div className="flex items-center justify-between border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-4 py-1.5 text-xs text-gray-600 dark:text-gray-400">
      <div className="flex items-center gap-4">
        {fileName && (
          <span className="font-medium text-gray-900 dark:text-gray-100">
            {fileName}
          </span>
        )}
        {filePath && (
          <span className="text-gray-500 dark:text-gray-500">{filePath}</span>
        )}
        <span className={`font-medium ${getStatusColor()}`}>
          {getStatusText()}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {cursorLine !== undefined && cursorColumn !== undefined && (
          <span>
            行 {cursorLine}, 列 {cursorColumn}
          </span>
        )}
        {totalLines !== undefined && <span>共 {totalLines} 行</span>}
        {totalChars !== undefined && <span>共 {totalChars} 字符</span>}
      </div>
    </div>
  );
}
