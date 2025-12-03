// 代碼功能說明：PDF 文件預覽組件
// 創建日期：2025-01-27
// 創建人：Daniel Chung
// 最後修改日期：2025-01-27

import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCw } from 'lucide-react';
import { useLanguage } from '../contexts/languageContext';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// 設置 PDF.js worker
// 使用 CDN 方式（更簡單，不需要額外依賴）
if (typeof window !== 'undefined') {
  pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
}

interface PDFViewerProps {
  fileUrl: string;
  fileName: string;
}

export default function PDFViewer({ fileUrl, fileName }: PDFViewerProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [rotation, setRotation] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF 加載錯誤:', error);
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
    <div className="p-4 h-full flex flex-col theme-transition">
      {/* 文件標題欄和工具欄 */}
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-primary">
        <div className="flex items-center">
          <i className="fa-solid fa-file-pdf text-red-400 mr-2"></i>
          <span className="font-medium text-primary">{fileName}</span>
        </div>
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
            onClick={() => window.open(fileUrl, '_blank')}
          >
            <i className="fa-solid fa-download"></i>
          </button>
        </div>
      </div>

      {/* PDF 內容區域 */}
      <div className="flex-1 overflow-auto bg-gray-100 dark:bg-gray-900 flex items-start justify-center p-4">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <div className="text-tertiary">{t('pdfViewer.loading', '加載中...')}</div>
          </div>
        )}
        {error && (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <i className="fa-solid fa-exclamation-triangle text-4xl mb-2"></i>
            <p>{t('pdfViewer.error', '無法加載 PDF')}</p>
            <p className="text-sm text-tertiary mt-2">{error}</p>
          </div>
        )}
        {!loading && !error && (
          <Document
            file={fileUrl}
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
