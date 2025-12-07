/**
 * 代碼功能說明: 文件預覽組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 */

import React, { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';
import { previewFile, FileMetadata } from '../lib/api';
import PDFViewer from './PDFViewer';
import MarkdownViewer from './MarkdownViewer';

interface FilePreviewProps {
  file: FileMetadata;
  isOpen: boolean;
  onClose: () => void;
}

export default function FilePreview({ file, isOpen, onClose }: FilePreviewProps) {
  const [content, setContent] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  useEffect(() => {
    if (isOpen && file) {
      loadPreview();
    }
  }, [isOpen, file]);

  const loadPreview = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await previewFile(file.file_id);
      if (response.success && response.data) {
        setContent(response.data.content);
        setIsTruncated(response.data.is_truncated);
      } else {
        setError('預覽失敗');
      }
    } catch (err: any) {
      setError(err.message || '預覽失敗');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="text-center py-8 text-red-500">
          {error}
        </div>
      );
    }

    // PDF 文件使用 PDFViewer
    if (file.file_type === 'application/pdf') {
      return <PDFViewer fileId={file.file_id} />;
    }

    // Markdown 文件使用 MarkdownViewer
    if (file.file_type === 'text/markdown' || file.filename.endsWith('.md')) {
      return <MarkdownViewer content={content} />;
    }

    // 其他文本文件直接显示
    return (
      <div className="p-4">
        <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded">
          {content}
        </pre>
        {isTruncated && (
          <div className="mt-2 text-sm text-gray-500">
            文件內容已截斷（僅顯示前 100KB）
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold truncate">{file.filename}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {renderContent()}
        </div>

        {/* Footer */}
        <div className="p-4 border-t text-sm text-gray-500">
          <div className="flex justify-between">
            <span>文件大小: {file.file_size} bytes</span>
            <span>類型: {file.file_type}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
