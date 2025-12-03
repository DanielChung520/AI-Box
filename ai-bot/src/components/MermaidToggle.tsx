// 代碼功能說明：Mermaid 圖形切換組件，支持代碼和圖形視圖切換
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useState } from 'react';
import { Code2, BarChart3 } from 'lucide-react';
import MermaidRenderer from './MermaidRenderer';
import { useLanguage } from '../contexts/languageContext';

interface MermaidToggleProps {
  code: string;
  className?: string;
}

export default function MermaidToggle({ code, className = '' }: MermaidToggleProps) {
  const [showCode, setShowCode] = useState(false);
  const { t } = useLanguage();

  const toggleView = () => {
    setShowCode(!showCode);
  };

  return (
    <div className={`relative my-4 rounded-lg overflow-hidden border border-primary bg-secondary ${className}`}>
      {/* 切換按鈕 */}
      <div className="flex items-center justify-between px-4 py-2 bg-tertiary border-b border-primary">
        <span className="text-xs font-mono text-tertiary opacity-70">
          mermaid
        </span>
        <button
          onClick={toggleView}
          className="flex items-center gap-2 px-3 py-1 text-xs text-tertiary hover:text-primary transition-colors rounded hover:bg-hover"
          title={showCode ? (t('mermaid.showChart') || '顯示圖表') : (t('mermaid.showCode') || '顯示代碼')}
          aria-label={showCode ? (t('mermaid.showChart') || '顯示圖表') : (t('mermaid.showCode') || '顯示代碼')}
        >
          {showCode ? (
            <>
              <BarChart3 className="w-4 h-4" />
              <span>{t('mermaid.showChart') || '顯示圖表'}</span>
            </>
          ) : (
            <>
              <Code2 className="w-4 h-4" />
              <span>{t('mermaid.showCode') || '顯示代碼'}</span>
            </>
          )}
        </button>
      </div>

      {/* 內容區域 */}
      <div className="p-4">
        {showCode ? (
          // 顯示代碼
          <pre className="text-sm text-primary font-mono whitespace-pre-wrap overflow-x-auto">
            <code>{code}</code>
          </pre>
        ) : (
          // 顯示圖表
          <MermaidRenderer code={code} className="bg-transparent" />
        )}
      </div>
    </div>
  );
}
