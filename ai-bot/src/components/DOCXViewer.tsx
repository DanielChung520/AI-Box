// 代碼功能說明：DOCX 文件預覽組件
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useState, useEffect } from 'react';
import mammoth from 'mammoth';
import { useLanguage } from '../contexts/languageContext';

interface DOCXViewerProps {
  fileUrl: string;
  fileName: string;
}

export default function DOCXViewer({ fileUrl, fileName }: DOCXViewerProps) {
  const [htmlContent, setHtmlContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();

  useEffect(() => {
    const loadDocument = async () => {
      try {
        setLoading(true);
        setError(null);

        // 獲取 DOCX 文件
        const response = await fetch(fileUrl);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const arrayBuffer = await response.arrayBuffer();

        // 使用 mammoth 將 DOCX 轉換為 HTML
        const result = await mammoth.convertToHtml(
          { arrayBuffer },
          {
            styleMap: [
              "p[style-name='Heading 1'] => h1:fresh",
              "p[style-name='Heading 2'] => h2:fresh",
              "p[style-name='Heading 3'] => h3:fresh",
            ],
          }
        );

        setHtmlContent(result.value);
        setLoading(false);

        // 如果有警告，記錄但不阻止顯示
        if (result.messages.length > 0) {
          console.warn('DOCX 轉換警告:', result.messages);
        }
      } catch (err: any) {
        console.error('DOCX 加載錯誤:', err);
        setError(err.message || '無法加載 DOCX 文件');
        setLoading(false);
      }
    };

    loadDocument();
  }, [fileUrl]);

  return (
    <div className="p-4 h-full flex flex-col theme-transition">
      {/* 文件標題欄 */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-primary">
        <div className="flex items-center">
          <i className="fa-solid fa-file-word text-blue-400 mr-2"></i>
          <span className="font-medium text-primary">{fileName}</span>
        </div>
        <div className="flex space-x-2">
          <button
            className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            title={t('docxViewer.download', '下載')}
            onClick={() => window.open(fileUrl, '_blank')}
          >
            <i className="fa-solid fa-download"></i>
          </button>
          <button
            className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            title={t('docxViewer.more', '更多')}
          >
            <i className="fa-solid fa-ellipsis-vertical"></i>
          </button>
        </div>
      </div>

      {/* DOCX 內容區域 */}
      <div className="flex-1 overflow-y-auto">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-tertiary">{t('docxViewer.loading', '加載中...')}</div>
          </div>
        )}
        {error && (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <i className="fa-solid fa-exclamation-triangle text-4xl mb-2"></i>
            <p>{t('docxViewer.error', '無法加載 DOCX 文件')}</p>
            <p className="text-sm text-tertiary mt-2">{error}</p>
          </div>
        )}
        {!loading && !error && (
          <div
            className="docx-content p-4"
            dangerouslySetInnerHTML={{ __html: htmlContent }}
            style={{
              color: 'inherit',
            }}
          />
        )}
      </div>
    </div>
  );
}
