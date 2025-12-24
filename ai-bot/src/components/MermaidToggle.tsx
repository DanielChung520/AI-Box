// 代碼功能說明：Mermaid 圖形切換組件，支持代碼和圖形視圖切換
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useState } from 'react';
import { Code2, BarChart3, Copy, Check, Maximize2, X, ZoomIn, ZoomOut } from 'lucide-react';
import MermaidRenderer from './MermaidRenderer';
import { useLanguage } from '../contexts/languageContext';

interface MermaidToggleProps {
  code: string;
  className?: string;
}

export default function MermaidToggle({ code, className = '' }: MermaidToggleProps) {
  const [showCode, setShowCode] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(1);
  const { t } = useLanguage();

  const toggleView = () => {
    setShowCode(!showCode);
  };

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 0.25, 3)); // 最大 300%
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 0.25, 0.5)); // 最小 50%
  };

  const handleZoomReset = () => {
    setZoomLevel(1);
  };

  const handleModalClose = () => {
    setShowModal(false);
    setZoomLevel(1); // 關閉時重置縮放
  };

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

  return (
    <div className={`relative my-4 rounded-lg overflow-hidden border border-primary bg-secondary ${className}`}>
      {/* 工具欄：語言標籤、切換按鈕、複製按鈕 */}
      <div className="flex items-center justify-between px-4 py-2 bg-tertiary border-b border-primary">
        <span className="text-xs font-mono text-tertiary opacity-70">
          mermaid
        </span>
        <div className="flex items-center gap-2">
          {/* 切換按鈕 */}
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
          {/* 放大按鈕（僅在圖形模式下顯示） */}
          {!showCode && (
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-1 px-2 py-1 text-xs text-tertiary hover:text-primary transition-colors rounded hover:bg-hover"
              title={t('mermaid.zoom') || '放大圖表'}
              aria-label={t('mermaid.zoom') || '放大圖表'}
            >
              <Maximize2 className="w-3 h-3" />
            </button>
          )}
          {/* 複製代碼按鈕 */}
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
      </div>

      {/* 內容區域 */}
      <div className="p-4">
        {showCode ? (
          // 顯示代碼
          <pre className="text-sm text-primary font-mono whitespace-pre-wrap overflow-x-auto">
            <code>{code}</code>
          </pre>
        ) : (
          // 顯示圖表（支持雙擊放大）
          <div
            onDoubleClick={() => setShowModal(true)}
            className="cursor-pointer"
            title={t('mermaid.doubleClickToZoom') || '雙擊放大圖表'}
          >
            <MermaidRenderer code={code} className="bg-transparent" />
          </div>
        )}
      </div>

      {/* 放大圖表的模態視窗 */}
      {showModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={handleModalClose}
        >
          <div
            className="relative w-[90vw] h-[90vh] max-w-7xl max-h-[90vh] bg-secondary rounded-lg shadow-2xl overflow-hidden border border-primary/30"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 模態視窗標題欄 */}
            <div className="flex items-center justify-between px-4 py-3 bg-tertiary/60 border-b border-primary/30">
              <span className="text-sm font-semibold text-primary">
                {t('mermaid.chartViewer') || 'Mermaid 圖表視圖'}
              </span>
              <div className="flex items-center gap-2">
                {/* 縮放控制按鈕組 */}
                <div className="flex items-center gap-1 border-r border-primary/30 pr-2 mr-2">
                  <button
                    onClick={handleZoomOut}
                    className={`flex items-center justify-center w-8 h-8 transition-colors rounded hover:bg-hover font-mono ${
                      zoomLevel <= 0.5
                        ? 'text-tertiary/50 cursor-not-allowed'
                        : 'text-tertiary hover:text-primary'
                    }`}
                    title={t('mermaid.zoomOut') || '縮小'}
                    aria-label={t('mermaid.zoomOut') || '縮小'}
                    disabled={zoomLevel <= 0.5}
                  >
                    <ZoomOut className="w-4 h-4" />
                  </button>
                  <button
                    onClick={handleZoomReset}
                    className="flex items-center justify-center w-12 h-8 text-xs text-tertiary hover:text-primary transition-colors rounded hover:bg-hover font-mono"
                    title={t('mermaid.zoomReset') || '重置縮放'}
                    aria-label={t('mermaid.zoomReset') || '重置縮放'}
                  >
                    {Math.round(zoomLevel * 100)}%
                  </button>
                  <button
                    onClick={handleZoomIn}
                    className={`flex items-center justify-center w-8 h-8 transition-colors rounded hover:bg-hover ${
                      zoomLevel >= 3
                        ? 'text-tertiary/50 cursor-not-allowed'
                        : 'text-tertiary hover:text-primary'
                    }`}
                    title={t('mermaid.zoomIn') || '放大'}
                    aria-label={t('mermaid.zoomIn') || '放大'}
                    disabled={zoomLevel >= 3}
                  >
                    <ZoomIn className="w-4 h-4" />
                  </button>
                </div>
                {/* 關閉按鈕 */}
                <button
                  onClick={handleModalClose}
                  className="flex items-center justify-center w-8 h-8 text-tertiary hover:text-primary transition-colors rounded hover:bg-hover"
                  title={t('mermaid.close') || '關閉'}
                  aria-label={t('mermaid.close') || '關閉'}
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* 模態視窗內容區域 */}
            <div className="p-6 h-[calc(90vh-60px)] overflow-auto">
              <div
                style={{
                  transform: `scale(${zoomLevel})`,
                  transformOrigin: 'top left',
                  transition: 'transform 0.2s ease-in-out',
                }}
              >
                <MermaidRenderer code={code} className="bg-transparent" />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
