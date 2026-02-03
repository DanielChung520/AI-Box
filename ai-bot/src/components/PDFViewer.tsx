// 代碼功能說明：PDF 文件預覽組件
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2026-02-01 UTC+8

import { useState, useEffect, useMemo } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { useLanguage } from '../contexts/languageContext';
import { downloadFile } from '../lib/api';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// 設置 PDF.js worker
// 使用 unpkg CDN（更可靠，支持所有版本）
// 注意：pdfjs-dist 5.x 版本使用 .mjs 扩展名
if (typeof window !== 'undefined') {
  // 尝试使用 .mjs 扩展名（新版本）
  const workerUrl = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;
  pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
  console.log('[PDFViewer] PDF.js worker URL:', workerUrl);
}

import { FileMetadata } from '../lib/api';

interface PDFViewerProps {
  fileId: string;
  fileName: string;
  fileUrl?: string; // 保留作為可選參數，用於向後兼容
  fileMetadata?: FileMetadata; // 文件元數據（包含 storage_path，用於 SeaWeedFS 直接訪問）
  showHeader?: boolean; // 是否顯示 Header（默認 true）
}

export default function PDFViewer({ fileId, fileName, fileUrl, fileMetadata, showHeader = true }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfData, setPdfData] = useState<ArrayBuffer | string | null>(null);
  const { t } = useLanguage();

  // 使用 useMemo 缓存 options，避免不必要的重新渲染
  const documentOptions = useMemo(() => ({
    cMapUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/cmaps/`,
    cMapPacked: true,
    standardFontDataUrl: `https://unpkg.com/pdfjs-dist@${pdfjs.version}/standard_fonts/`,
  }), []);

  // 下載 PDF 文件並創建 Blob URL
  useEffect(() => {
    let currentBlobUrl: string | null = null;

    const loadPdf = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log('[PDFViewer] 開始加載 PDF 文件:', { fileId, fileName });

        // 使用 downloadFile API 下載文件（自動處理認證）
        // 如果提供了 fileMetadata 且包含 storage_path，優先使用 SeaWeedFS 直接訪問
        const blob = await downloadFile(fileId, fileMetadata);
        console.log('[PDFViewer] 文件下載成功，大小:', blob.size, 'bytes', '類型:', blob.type);

        if (blob.size === 0) {
          throw new Error('下載的文件為空');
        }

        // 檢查文件類型
        if (blob.type !== 'application/pdf' && !fileName.toLowerCase().endsWith('.pdf')) {
          console.warn('[PDFViewer] 文件類型可能不是 PDF:', blob.type);
        }

        // 將 Blob 轉換為 ArrayBuffer（react-pdf 對 ArrayBuffer 的支持更穩定）
        const arrayBuffer = await blob.arrayBuffer();
        console.log('[PDFViewer] 轉換為 ArrayBuffer 成功，大小:', arrayBuffer.byteLength, 'bytes');

        // 同時創建 Blob URL 作為備選（用於下載等功能）
        const pdfBlob = new Blob([arrayBuffer], { type: 'application/pdf' });
        const blobUrl = URL.createObjectURL(pdfBlob);
        currentBlobUrl = blobUrl;
        setPdfBlobUrl(blobUrl);

        // 使用 ArrayBuffer 作為 PDF 數據源
        setPdfData(arrayBuffer);
        console.log('[PDFViewer] PDF 數據準備完成，使用 ArrayBuffer');

        // 注意：loading 狀態將由 Document 組件的 onLoadSuccess 或 onLoadError 來設置

      } catch (err: any) {
        console.error('[PDFViewer] 加載錯誤:', err);
        setError(err.message || '無法加載 PDF 文件');
        setLoading(false);
      }
    };

    if (fileId) {
      loadPdf();
    } else if (fileUrl) {
      // 向後兼容：如果提供了 fileUrl，直接使用
      setPdfData(fileUrl);
      setPdfBlobUrl(fileUrl);
      setLoading(false);
    } else {
      setError('未提供文件 ID 或文件 URL');
      setLoading(false);
    }

    // 清理函數：組件卸載時釋放 Blob URL
    return () => {
      if (currentBlobUrl && currentBlobUrl.startsWith('blob:')) {
        URL.revokeObjectURL(currentBlobUrl);
      }
      // 也清理狀態中的 Blob URL
      setPdfBlobUrl((prev) => {
        if (prev && prev.startsWith('blob:')) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
      setPdfData(null);
    };
  }, [fileId, fileUrl, fileName]);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('[PDFViewer] PDF 加載成功，頁數:', numPages);
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('[PDFViewer] PDF 加載錯誤:', error);
    console.error('[PDFViewer] 錯誤詳情:', {
      name: error.name,
      message: error.message,
      stack: error.stack
    });
    setError(error.message || '無法加載 PDF 文件');
    setLoading(false);
  };

  const goToPrevPage = () => {
    setPageNumber(prev => Math.max(1, prev - 1));
  };

  const goToNextPage = () => {
    setPageNumber(prev => Math.min(numPages, prev + 1));
  };

  const zoomIn = () => {
    setScale(prev => Math.min(3.0, prev + 0.2));
  };

  const zoomOut = () => {
    setScale(prev => Math.max(0.5, prev - 0.2));
  };

  const rotate = () => {
    setRotation(prev => (prev + 90) % 360);
  };

  return (
    <div className="flex flex-col theme-transition" style={{ height: '100%', minHeight: 0 }}>
      {/* 工具欄：翻頁、縮放、旋轉、下載 - 始終顯示以支持 PDF 操作 */}
      {/* showHeader 僅控制檔名顯示，inline 模式下父組件已有檔名，不重複顯示 */}
      <div className="flex items-center justify-between p-4 pb-2 border-b border-primary flex-shrink-0">
        {/* 檔名區塊：僅在 showHeader 時顯示（非 inline 模式） */}
        {showHeader ? (
          <div className="flex items-center">
            <i className="fa-solid fa-file-pdf text-red-400 mr-2"></i>
            <span className="font-medium text-primary">{fileName}</span>
          </div>
        ) : (
          <div />
        )}
        <div className="flex items-center gap-2">
          {/* 頁面控制 */}
          <div className="flex items-center gap-2 px-2">
            <button
              onClick={goToPrevPage}
              disabled={pageNumber <= 1}
              className="p-1 rounded hover:bg-tertiary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('pdfViewer.prevPage', '上一頁')}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-sm text-tertiary">
              {pageNumber} / {numPages}
            </span>
            <button
              onClick={goToNextPage}
              disabled={pageNumber >= numPages}
              className="p-1 rounded hover:bg-tertiary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('pdfViewer.nextPage', '下一頁')}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          {/* 縮放控制 */}
          <div className="flex items-center gap-2 px-2 border-l border-primary">
            <button
              onClick={zoomOut}
              disabled={scale <= 0.5}
              className="p-1 rounded hover:bg-tertiary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('pdfViewer.zoomOut', '縮小')}
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <span className="text-sm text-tertiary min-w-[3rem] text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={zoomIn}
              disabled={scale >= 3.0}
              className="p-1 rounded hover:bg-tertiary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              title={t('pdfViewer.zoomIn', '放大')}
            >
              <ZoomIn className="w-4 h-4" />
            </button>
          </div>

          {/* 旋轉 */}
          <button
            onClick={rotate}
            className="p-1 rounded hover:bg-tertiary transition-colors"
            title={t('pdfViewer.rotate', '旋轉')}
          >
            <RotateCw className="w-4 h-4" />
          </button>

          {/* 下載 */}
          <button
            className="p-1 rounded hover:bg-tertiary transition-colors"
            title={t('pdfViewer.download', '下載')}
            onClick={async () => {
              if (!fileId) {
                // 如果沒有 fileId，使用 fileUrl 下載
                if (fileUrl) {
                  window.open(fileUrl, '_blank');
                } else {
                  alert('無法下載：未提供文件 ID 或文件 URL');
                }
                return;
              }
              try {
                const blob = await downloadFile(fileId);
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileName;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
              } catch (err: any) {
                console.error('[PDFViewer] 下載失敗:', err);
                alert(`下載失敗: ${err.message}`);
              }
            }}
          >
            <i className="fa-solid fa-download"></i>
          </button>
        </div>
      </div>

      {/* PDF 內容區域 */}
      <div className="flex-1 overflow-auto bg-gray-100 dark:bg-gray-900 flex items-start justify-center p-4" style={{ minHeight: 0 }}>
        {error && (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <i className="fa-solid fa-exclamation-triangle text-4xl mb-2"></i>
            <p>{t('pdfViewer.error', '無法加載 PDF')}</p>
            <p className="text-sm text-tertiary mt-2">{error}</p>
          </div>
        )}
        {!error && !pdfData && (
          <div className="flex items-center justify-center h-full">
            <div className="text-tertiary">{t('pdfViewer.loading', '加載中...')}</div>
          </div>
        )}
        {!error && pdfData && (
          <Document
            file={pdfData}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center justify-center h-full">
                <div className="text-tertiary">{t('pdfViewer.loading', '加載中...')}</div>
              </div>
            }
            error={
              <div className="flex flex-col items-center justify-center h-full text-red-400">
                <i className="fa-solid fa-exclamation-triangle text-4xl mb-2"></i>
                <p>{t('pdfViewer.error', '無法加載 PDF')}</p>
              </div>
            }
            options={documentOptions}
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              rotate={rotation}
              className="shadow-lg"
              renderTextLayer={true}
              renderAnnotationLayer={true}
            />
          </Document>
        )}
      </div>
    </div>
  );
}
