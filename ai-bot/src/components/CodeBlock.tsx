// 代碼功能說明：代碼塊組件，支持語法高亮和複製功能
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useState, useMemo } from 'react';
import { Highlight, themes } from 'prism-react-renderer';
import type { RenderProps, Token } from 'prism-react-renderer';
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

  // 調試：記錄渲染信息
  if (process.env.NODE_ENV === 'development') {
    console.debug('[CodeBlock] Rendering:', { language, codeLength: code.length });
  }

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
    <div className="chat-code-block relative my-4 rounded-lg overflow-hidden bg-secondary shadow-md" style={{ border: '0.5px solid rgb(148 163 184 / 0.2)' }}>
      {/* 語言標籤和複製按鈕 */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-tertiary/60" style={{ borderBottom: '0.5px solid rgb(148 163 184 / 0.2)' }}>
        <span className="text-xs font-mono text-primary/70 font-semibold uppercase tracking-wide">
          {language}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-0.5 text-xs text-tertiary hover:text-primary transition-colors rounded hover:bg-hover"
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
        <Highlight theme={prismTheme as any} code={code} language={language as any}>
          {({ className, style, tokens, getLineProps, getTokenProps }: RenderProps) => (
            <pre
              className={className}
              style={{
                ...style,
                margin: 0,
                padding: '1rem',
                fontSize: '0.875rem',
                lineHeight: '1.6',
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace',
                overflow: 'auto',
              }}
            >
              {tokens.map((line: Token[], i: number) => {
                const lineProps = getLineProps({ line, key: i });
                // 分離 key，避免 React 警告（key 不能通過 spread 傳遞）
                const { key: lineKey, ...linePropsWithoutKey } = lineProps;
                return (
                  <div key={lineKey || i} {...(linePropsWithoutKey as any)}>
                    {line.map((token: Token, key: number) => {
                      const tokenProps = getTokenProps({ token, key });
                      // 分離 key，避免 React 警告（key 不能通過 spread 傳遞）
                      const { key: tokenKey, ...tokenPropsWithoutKey } = tokenProps;
                      return (
                        <span
                          key={tokenKey || key}
                          {...(tokenPropsWithoutKey as any)}
                          style={{
                            ...tokenPropsWithoutKey.style,
                            // 確保樣式被正確應用
                          }}
                        />
                      );
                    })}
                  </div>
                );
              })}
            </pre>
          )}
        </Highlight>
      </div>
    </div>
  );
}
