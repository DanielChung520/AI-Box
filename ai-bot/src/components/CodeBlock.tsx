// 代碼功能說明：代碼塊組件，支持語法高亮和複製功能
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useState, useMemo } from 'react';
import { Prism as SyntaxHighlighter, themes } from 'prism-react-renderer';
import { Copy, Check } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { useLanguage } from '../contexts/languageContext';

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language = 'text' }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const { theme } = useTheme();
  const { t } = useLanguage();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('複製失敗:', err);
      // 降級方案：使用傳統方法
      const textArea = document.createElement('textarea');
      textArea.value = code;
      textArea.style.position = 'fixed';
      textArea.style.opacity = '0';
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch (fallbackErr) {
        console.error('降級複製方法也失敗:', fallbackErr);
      }
      document.body.removeChild(textArea);
    }
  };

  // 根據主題選擇代碼高亮主題
  const prismTheme = useMemo(() => {
    try {
      if (theme === 'dark') {
        return themes.vsDark;
      } else {
        return themes.vsLight;
      }
    } catch (error) {
      console.warn('無法加載 Prism 主題，使用默認主題:', error);
      // 返回一個簡單的默認主題
      return {
        plain: { color: theme === 'dark' ? '#e2e8f0' : '#1f2937', backgroundColor: 'transparent' },
        styles: []
      };
    }
  }, [theme]);

  return (
    <div className="relative my-4 rounded-lg overflow-hidden border border-primary bg-secondary">
      {/* 語言標籤和複製按鈕 */}
      <div className="flex items-center justify-between px-4 py-2 bg-tertiary border-b border-primary">
        <span className="text-xs font-mono text-tertiary opacity-70">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 text-xs text-tertiary hover:text-primary transition-colors rounded hover:bg-hover"
          title={t('codeBlock.copy') || '複製代碼'}
          aria-label={t('codeBlock.copy') || '複製代碼'}
        >
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              <span>{t('codeBlock.copied') || '已複製'}</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>{t('codeBlock.copy') || '複製'}</span>
            </>
          )}
        </button>
      </div>

      {/* 代碼內容 */}
      <div className="overflow-x-auto">
        <SyntaxHighlighter
          language={language}
          style={prismTheme}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: '1rem',
            backgroundColor: 'transparent',
            fontSize: '0.875rem',
            lineHeight: '1.5',
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
