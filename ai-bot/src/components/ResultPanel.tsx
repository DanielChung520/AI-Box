import { useState } from 'react';
import { useLanguage } from '../contexts/languageContext';
import { cn } from '../lib/utils';
import FileTree from './FileTree';
import FileViewer from './FileViewer';

interface ResultPanelProps {
  collapsed: boolean;
  onToggle: () => void;
  onViewChange?: (isMarkdownView: boolean) => void;
}

export default function ResultPanel({ collapsed, onToggle, onViewChange }: ResultPanelProps) {
  const [activeTab, setActiveTab] = useState<'files' | 'preview'>('files');
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const { t } = useLanguage();

  // 模擬文件 URL（實際應該從 API 獲取）
  const getFileUrl = (fileName: string): string => {
    // 這裡應該根據實際情況構建文件 URL
    // 暫時使用模擬 URL
    return `/api/files/${encodeURIComponent(fileName)}`;
  };

  // 模擬文件內容（僅用於 Markdown，其他類型從 URL 加載）
  const getFileContent = (fileName: string): string | undefined => {
    const extension = fileName.split('.').pop()?.toLowerCase();
    if (extension === 'md' || extension === 'markdown') {
      // 模擬 Markdown 內容
      return `# ${fileName}

## 概述
這是一個示例文件內容。

## 內容

這是一個支持多種文件格式預覽的文件查看器。

### 支持的文件類型
- Markdown (.md)
- PDF (.pdf)
- DOCX (.docx)

*文件生成時間: 2025-01-27*`;
    }
    return undefined;
  };

  const handleFileSelect = (fileId: string) => {
    setSelectedFile(fileId);
    setActiveTab('preview');
    if (onViewChange) {
      onViewChange(true);
    }
  };

  return (
    <div className={cn(
      "h-full bg-secondary border-l border-primary flex flex-col transition-all duration-300 w-full theme-transition"
    )}>
      {/* 结果面板头部 */}
      <div className="p-4 border-b border-primary flex items-center">
        <div className="flex space-x-2">
          <button
            className={`px-3 py-1 rounded-t-lg text-sm ${activeTab === 'files' ? 'bg-tertiary text-primary' : 'text-tertiary'}`}
            onClick={() => {
              setActiveTab('files');
              if (onViewChange) {
                onViewChange(false);
              }
            }}
          >
            {t('resultPanel.files')}
          </button>
          <button
            className={`px-3 py-1 rounded-t-lg text-sm ${activeTab === 'preview' ? 'bg-tertiary text-primary' : 'text-tertiary'}`}
            onClick={() => {
              if (selectedFile) {
                setActiveTab('preview');
                if (onViewChange) {
                  onViewChange(true);
                }
              }
            }}
            disabled={!selectedFile}
          >
            {t('resultPanel.preview')}
          </button>
        </div>
      </div>

      {/* 结果面板内容 */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'files' && (
          <FileTree onFileSelect={handleFileSelect} />
        )}
        {activeTab === 'preview' && selectedFile && (
          <FileViewer
            fileUrl={getFileUrl(selectedFile)}
            fileName={selectedFile}
            content={getFileContent(selectedFile)}
          />
        )}
        {activeTab === 'preview' && !selectedFile && (
          <div className="p-4 h-full flex items-center justify-center text-tertiary">
            {t('resultPanel.noFileSelected', '請選擇一個文件進行預覽')}
          </div>
        )}
      </div>
    </div>
  );
}
