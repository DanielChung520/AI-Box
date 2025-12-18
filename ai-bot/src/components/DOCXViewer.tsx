/**
 * 代碼功能說明: DOCX 文件預覽組件
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-01-27
 */

import { useState, useEffect } from 'react';
import mammoth from 'mammoth';
import { Loader2, FileText } from 'lucide-react';
import { downloadFile } from '../lib/api';

interface DOCXViewerProps {
  fileId: string;
  fileName: string;
}

export default function DOCXViewer({ fileId, fileName }: DOCXViewerProps) {
  const [htmlContent, setHtmlContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadDocx = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log('[DOCXViewer] 開始加載文件:', fileId);

        // 使用 downloadFile API 函數（自動處理認證）
        const blob = await downloadFile(fileId);
        console.log('[DOCXViewer] 文件下載成功，大小:', blob.size, 'bytes');

        if (blob.size === 0) {
          throw new Error('下載的文件為空');
        }

        const arrayBuffer = await blob.arrayBuffer();
        console.log('[DOCXViewer] 轉換為 ArrayBuffer 成功，大小:', arrayBuffer.byteLength, 'bytes');

        // 使用 mammoth 將 DOCX 轉換為 HTML
        const result = await mammoth.convertToHtml({ arrayBuffer });
        console.log('[DOCXViewer] DOCX 轉換為 HTML 成功');

        setHtmlContent(result.value);

        // 如果有警告，記錄但不阻止渲染
        if (result.messages.length > 0) {
          console.warn('[DOCXViewer] 轉換警告:', result.messages);
        }
      } catch (err: any) {
        console.error('[DOCXViewer] 加載錯誤:', err);
        console.error('[DOCXViewer] 錯誤詳情:', {
          message: err.message,
          stack: err.stack,
          name: err.name,
          status: err.status,
          fileId: fileId
        });

        // 構建更詳細的錯誤信息
        let errorMessage = '無法加載 DOCX 文件';

        if (err.message) {
          errorMessage = err.message;
        } else if (err.status === 401) {
          errorMessage = '認證失敗，請重新登錄';
        } else if (err.status === 404) {
          errorMessage = '文件不存在';
        } else if (err.status === 403) {
          errorMessage = '沒有權限訪問此文件';
        } else if (err.status) {
          errorMessage = `服務器錯誤 (${err.status})`;
        }

        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    };

    if (fileId) {
      loadDocx();
    } else {
      setError('文件 ID 無效');
      setLoading(false);
    }
  }, [fileId]);

  return (
    <div className="p-4 h-full flex flex-col theme-transition">
      {/* 文件標題欄 */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-primary">
        <div className="flex items-center">
          <i className="fa-solid fa-file-word text-blue-400 mr-2"></i>
          <span className="font-medium text-primary">{fileName}</span>
        </div>
      </div>

      {/* 內容區域 */}
      <div className="flex-1 overflow-auto bg-white dark:bg-gray-900 p-6">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-blue-500 mr-2" />
            <span className="text-tertiary">加載中...</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <FileText className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg font-semibold">無法加載 DOCX 文件</p>
            <p className="text-sm text-tertiary mt-2 max-w-md text-center">{error}</p>
            <div className="mt-4 text-xs text-tertiary max-w-md text-center">
              <p>提示：請檢查：</p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>文件是否已成功上傳</li>
                <li>後端是否支持 DOCX 文件下載</li>
                <li>網絡連接是否正常</li>
                <li>是否已正確登錄</li>
              </ul>
            </div>
          </div>
        )}

        {!loading && !error && (
          <div
            className="docx-content prose prose-lg max-w-none text-primary"
            style={{
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}
            dangerouslySetInnerHTML={{ __html: htmlContent }}
          />
        )}
      </div>
    </div>
  );
}
