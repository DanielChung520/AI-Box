/**
 * 代碼功能說明: Excel (XLSX) 文件預覽組件
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2026-01-21 11:57 UTC+8
 */

import { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { Loader2, FileSpreadsheet } from 'lucide-react';
import { downloadFile, FileMetadata } from '../lib/api';

interface ExcelViewerProps {
  fileId: string;
  fileName: string;
  fileMetadata?: FileMetadata; // 文件元數據（包含 storage_path，用於 SeaWeedFS 直接訪問）
  showHeader?: boolean; // 是否顯示 Header（默認 true）
}

interface SheetData {
  name: string;
  data: any[][];
}

export default function ExcelViewer({ fileId, fileName, fileMetadata, showHeader = true }: ExcelViewerProps) {
  const [sheets, setSheets] = useState<SheetData[]>([]);
  const [activeSheetIndex, setActiveSheetIndex] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadExcel = async () => {
      try {
        setLoading(true);
        setError(null);

        console.log('[ExcelViewer] 開始加載文件:', fileId);

        // 使用 downloadFile API 函數（自動處理認證）
        // 如果提供了 fileMetadata 且包含 storage_path，優先使用 SeaWeedFS 直接訪問
        const blob = await downloadFile(fileId, fileMetadata);
        console.log('[ExcelViewer] 文件下載成功，大小:', blob.size, 'bytes');

        if (blob.size === 0) {
          throw new Error('下載的文件為空');
        }

        const arrayBuffer = await blob.arrayBuffer();
        console.log('[ExcelViewer] 轉換為 ArrayBuffer 成功，大小:', arrayBuffer.byteLength, 'bytes');

        // 使用 xlsx 解析 Excel 文件
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        console.log('[ExcelViewer] Excel 文件解析成功，工作表數量:', workbook.SheetNames.length);

        // 轉換所有工作表為數據
        const sheetData: SheetData[] = workbook.SheetNames.map((sheetName) => {
          const worksheet = workbook.Sheets[sheetName];
          // 將工作表轉換為二維數組
          const data = XLSX.utils.sheet_to_json(worksheet, {
            header: 1,
            defval: '' // 空單元格使用空字符串
          }) as any[][];

          return {
            name: sheetName,
            data: data
          };
        });

        setSheets(sheetData);

        if (sheetData.length === 0) {
          throw new Error('Excel 文件中沒有工作表');
        }
      } catch (err: any) {
        console.error('[ExcelViewer] 加載錯誤:', err);
        console.error('[ExcelViewer] 錯誤詳情:', {
          message: err.message,
          stack: err.stack,
          name: err.name,
          status: err.status,
          fileId: fileId
        });

        // 構建更詳細的錯誤信息
        let errorMessage = '無法加載 Excel 文件';

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
      loadExcel();
    } else {
      setError('文件 ID 無效');
      setLoading(false);
    }
  }, [fileId]);

  const activeSheet = sheets[activeSheetIndex];

  return (
    <div className="p-4 h-full flex flex-col theme-transition">
      {/* 文件標題欄和工作表切換 */}
      {showHeader && (
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-primary">
        <div className="flex items-center gap-4">
          <div className="flex items-center">
            <i className="fa-solid fa-file-excel text-green-400 mr-2"></i>
            <span className="font-medium text-primary">{fileName}</span>
          </div>

          {/* 工作表切換 */}
          {sheets.length > 1 && (
            <div className="flex items-center gap-2">
              <span className="text-sm text-tertiary">工作表:</span>
              <select
                value={activeSheetIndex}
                onChange={(e) => setActiveSheetIndex(Number(e.target.value))}
                className="px-3 py-1 rounded border border-primary bg-secondary text-primary text-sm"
              >
                {sheets.map((sheet, index) => (
                  <option key={index} value={index}>
                    {sheet.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {sheets.length > 1 && (
          <div className="text-sm text-tertiary">
            {activeSheetIndex + 1} / {sheets.length}
          </div>
        )}
      </div>
      )}

      {/* 內容區域 */}
      <div className="flex-1 overflow-auto bg-white dark:bg-gray-900">
        {loading && (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-green-500 mr-2" />
            <span className="text-tertiary">加載中...</span>
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full text-red-400">
            <FileSpreadsheet className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg font-semibold">無法加載 Excel 文件</p>
            <p className="text-sm text-tertiary mt-2 max-w-md text-center">{error}</p>
            <div className="mt-4 text-xs text-tertiary max-w-md text-center">
              <p>提示：請檢查：</p>
              <ul className="list-disc list-inside mt-2 space-y-1">
                <li>文件是否已成功上傳</li>
                <li>後端是否支持 Excel 文件下載</li>
                <li>網絡連接是否正常</li>
                <li>是否已正確登錄</li>
              </ul>
            </div>
          </div>
        )}

        {!loading && !error && activeSheet && (
          <div className="p-4">
            <table className="min-w-full border-collapse border border-primary text-sm">
              <tbody>
                {activeSheet.data.map((row, rowIndex) => (
                  <tr key={rowIndex} className="border-b border-primary">
                    {row.map((cell, cellIndex) => {
                      // 第一行作為表頭
                      const isHeader = rowIndex === 0;
                      const CellTag = isHeader ? 'th' : 'td';

                      return (
                        <CellTag
                          key={cellIndex}
                          className={`px-4 py-2 text-left border-r border-primary ${
                            isHeader
                              ? 'bg-tertiary font-bold text-primary'
                              : 'text-primary bg-white dark:bg-gray-900'
                          }`}
                        >
                          {cell !== null && cell !== undefined ? String(cell) : ''}
                        </CellTag>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>

            {activeSheet.data.length === 0 && (
              <div className="text-center py-8 text-tertiary">
                <p>此工作表為空</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
