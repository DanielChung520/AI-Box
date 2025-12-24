/**
 * 代碼功能說明: 文件搜尋對話框組件
 * 創建日期: 2025-01-27
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-13 18:28:38 (UTC+8)
 *
 * 功能說明:
 * - 仿照 Cursor 的文件搜尋功能
 * - 支持搜尋檔名和文件內容
 * - 顯示搜尋結果列表
 * - 支持快捷鍵操作（Cmd/Ctrl + P）
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { X, FileText, Search } from 'lucide-react';

interface FileSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onFileSelect?: (fileId: string, fileName: string) => void;
  taskId?: string;
  userId?: string;
  fileTree?: any[];
}

interface SearchResult {
  fileId: string;
  fileName: string;
  filePath: string;
  matchType: 'filename' | 'content';
  matchPreview?: string;
}

export default function FileSearchModal({
  isOpen,
  onClose,
  onFileSelect,
  taskId: _taskId,
  userId: _userId,
  fileTree,
}: FileSearchModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const resultsRef = useRef<HTMLDivElement>(null);

  // 當對話框打開時，聚焦輸入框
  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setSearchQuery('');
      setSearchResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // 處理搜尋
  const performSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    const results: SearchResult[] = [];

    try {
      // 1. 搜尋檔名
      if (fileTree) {
        const searchInTree = (nodes: any[], path: string = ''): void => {
          for (const node of nodes) {
            const currentPath = path ? `${path}/${node.name}` : node.name;

            // 檢查檔名是否匹配
            if (node.name.toLowerCase().includes(query.toLowerCase())) {
              results.push({
                fileId: node.id,
                fileName: node.name,
                filePath: currentPath,
                matchType: 'filename',
              });
            }

            // 如果是資料夾，遞歸搜尋
            if (node.children && node.children.length > 0) {
              searchInTree(node.children, currentPath);
            }
          }
        };

        searchInTree(fileTree);
      }

      // 2. TODO: 搜尋文件內容（需要調用後端 API）
      // 這裡暫時只搜尋檔名

      // 排序結果：檔名匹配優先
      results.sort((a, b) => {
        if (a.matchType === 'filename' && b.matchType !== 'filename') return -1;
        if (a.matchType !== 'filename' && b.matchType === 'filename') return 1;
        return a.fileName.localeCompare(b.fileName);
      });

      setSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  }, [fileTree]);

  // 當搜尋查詢改變時執行搜尋
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(searchQuery);
    }, 300); // 防抖：300ms 延遲

    return () => clearTimeout(timer);
  }, [searchQuery, performSearch]);

  // 處理鍵盤快捷鍵
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) =>
          prev < searchResults.length - 1 ? prev + 1 : prev
        );
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : 0));
      } else if (e.key === 'Enter' && searchResults.length > 0) {
        e.preventDefault();
        const selectedResult = searchResults[selectedIndex];
        if (selectedResult && onFileSelect) {
          onFileSelect(selectedResult.fileId, selectedResult.fileName);
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, searchResults, selectedIndex, onFileSelect, onClose]);

  // 滾動到選中的結果
  useEffect(() => {
    if (resultsRef.current && selectedIndex >= 0) {
      const selectedElement = resultsRef.current.children[selectedIndex] as HTMLElement;
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }, [selectedIndex]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 theme-transition"
      onClick={onClose}
    >
      <div
        className="bg-secondary border border-primary rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 標題欄 */}
        <div className="flex items-center justify-between p-4 border-b border-primary">
          <div className="flex items-center gap-2">
            <Search className="w-5 h-5 text-tertiary" />
            <h2 className="text-lg font-semibold text-primary">搜尋檔案</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-tertiary text-primary transition-colors"
            aria-label="關閉"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 搜尋輸入框 */}
        <div className="p-4 border-b border-primary">
          <div className="relative">
            <input
              ref={inputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSelectedIndex(0);
              }}
              placeholder="搜尋檔名或內容... (Cmd/Ctrl + P)"
              className="w-full px-4 py-2 pl-10 bg-tertiary border border-primary rounded-lg text-primary placeholder-tertiary focus:outline-none focus:ring-2 focus:ring-blue-500 theme-transition"
            />
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-tertiary" />
            {isSearching && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                <i className="fa-solid fa-spinner fa-spin text-tertiary"></i>
              </div>
            )}
          </div>
        </div>

        {/* 搜尋結果 */}
        <div className="flex-1 overflow-y-auto p-2">
          {searchQuery.trim() === '' ? (
            <div className="text-center py-8 text-tertiary">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>輸入關鍵字開始搜尋</p>
              <p className="text-sm mt-2">支持搜尋檔名和文件內容</p>
            </div>
          ) : searchResults.length === 0 && !isSearching ? (
            <div className="text-center py-8 text-tertiary">
              <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>未找到匹配的文件</p>
            </div>
          ) : (
            <div ref={resultsRef} className="space-y-1">
              {searchResults.map((result, index) => (
                <button
                  key={`${result.fileId}-${index}`}
                  onClick={() => {
                    if (onFileSelect) {
                      onFileSelect(result.fileId, result.fileName);
                      onClose();
                    }
                  }}
                  className={`w-full text-left px-4 py-2 rounded-lg transition-colors ${
                    index === selectedIndex
                      ? 'bg-blue-500/20 text-blue-400 border-l-2 border-blue-500'
                      : 'hover:bg-tertiary text-primary'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{result.fileName}</div>
                      <div className="text-sm text-tertiary truncate">{result.filePath}</div>
                      {result.matchPreview && (
                        <div className="text-xs text-tertiary mt-1 line-clamp-1">
                          {result.matchPreview}
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-tertiary px-2 py-1 bg-primary rounded">
                      {result.matchType === 'filename' ? '檔名' : '內容'}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 底部提示 */}
        <div className="px-4 py-2 border-t border-primary text-xs text-tertiary flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span>↑↓ 選擇</span>
            <span>Enter 打開</span>
            <span>Esc 關閉</span>
          </div>
          {searchResults.length > 0 && (
            <span>{searchResults.length} 個結果</span>
          )}
        </div>
      </div>
    </div>
  );
}
