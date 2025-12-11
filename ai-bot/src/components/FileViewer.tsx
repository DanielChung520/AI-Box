// 代碼功能說明：通用文件預覽組件，根據文件類型選擇對應的預覽器
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useMemo } from 'react';
import MarkdownViewer from './MarkdownViewer';
import PDFViewer from './PDFViewer';
import DOCXViewer from './DOCXViewer';

interface FileViewerProps {
  fileUrl: string;
  fileName: string;
  content?: string; // 對於 Markdown，可以直接傳入內容
  fileId?: string; // 文件 ID，用於獲取向量和圖譜數據
}

export default function FileViewer({ fileUrl, fileName, content, fileId }: FileViewerProps) {
  // 根據文件擴展名判斷文件類型
  const fileType = useMemo(() => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    return extension || 'unknown';
  }, [fileName]);

  // 根據文件類型渲染對應的預覽組件
  switch (fileType) {
    case 'md':
    case 'markdown':
      return (
        <MarkdownViewer
          content={content || ''}
          fileName={fileName}
          fileId={fileId}
        />
      );

    case 'pdf':
      return (
        <PDFViewer
          fileUrl={fileUrl}
          fileName={fileName}
        />
      );

    case 'docx':
    case 'doc':
      return (
        <DOCXViewer
          fileUrl={fileUrl}
          fileName={fileName}
        />
      );

    default:
      return (
        <div className="p-4 h-full flex flex-col items-center justify-center theme-transition">
          <i className="fa-solid fa-file text-4xl text-tertiary mb-4"></i>
          <p className="text-tertiary mb-2">{fileName}</p>
          <p className="text-sm text-tertiary">
            不支持預覽此文件類型（{fileType}）
          </p>
          <a
            href={fileUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 px-4 py-2 bg-primary text-secondary rounded-lg hover:bg-opacity-80 transition-colors"
          >
            下載文件
          </a>
        </div>
      );
  }
}
