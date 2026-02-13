/**
 * 代碼功能說明: 通用文件預覽組件，根據文件類型分發到對應預覽器
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-02-13
 * 
 * 此組件僅負責分發，不包含預覽邏輯
 */

import { useMemo } from 'react';
import MarkdownPreview from './MarkdownPreview';
import { FileType } from 'lucide-react';

interface FileViewerProps {
  fileUrl: string;
  fileName: string;
  content?: string;
  fileId?: string;
}

export default function FileViewer({ fileUrl, fileName, fileId }: FileViewerProps) {
  const fileType = useMemo(() => {
    return fileName.split('.').pop()?.toLowerCase() || 'unknown';
  }, [fileName]);

  // 路由分發
  switch (fileType) {
    case 'md':
    case 'markdown':
      return <MarkdownPreview fileId={fileId} fileName={fileName} />;
    
    case 'pdf':
    case 'docx':
    case 'doc':
    case 'xlsx':
    case 'xls':
      return <UnsupportedPreview fileType={fileType} fileName={fileName} fileId={fileId} />;
    
    default:
      return (
        <div className="h-full flex flex-col items-center justify-center p-4">
          <FileType className="w-16 h-16 text-gray-400 mb-4" />
          <p className="text-gray-500 text-center">不支持預覽此文件類型（{fileType}）</p>
          {fileId && (
            <a href={`/api/v1/files/${fileId}/download`} target="_blank" rel="noopener noreferrer" className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
              下載文件
            </a>
          )}
        </div>
      );
  }
}

// 不支持的預覽類型占位組件
function UnsupportedPreview({ fileType, fileName, fileId }: { fileType: string; fileName: string; fileId?: string }) {
  const iconMap: Record<string, string> = {
    pdf: '📄 PDF',
    docx: '📝 Word',
    doc: '📝 Word',
    xlsx: '📊 Excel',
    xls: '📊 Excel',
  };

  return (
    <div className="h-full flex flex-col items-center justify-center p-4">
      <div className="text-6xl mb-4">{iconMap[fileType] || '📁'}</div>
      <p className="text-gray-700 font-medium">{fileName}</p>
      <p className="text-gray-500 text-sm mt-2">{fileType.toUpperCase()} 預覽功能開發中</p>
      {fileId && (
        <a href={`/api/v1/files/${fileId}/download`} target="_blank" rel="noopener noreferrer" className="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
          下載文件
        </a>
      )}
    </div>
  );
}
