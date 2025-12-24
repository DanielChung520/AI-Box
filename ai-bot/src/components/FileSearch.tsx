/**
 * 代碼功能說明: 文件搜索組件
 * 創建日期: 2025-12-06
 * 創建人: Daniel Chung
 * 最後修改日期: 2025-12-06
 */

import React, { useState } from 'react';
import { Search, X } from 'lucide-react';
import { searchFiles, FileMetadata } from '../lib/api';

interface FileSearchProps {
  userId?: string;
  onFileSelect?: (file: FileMetadata) => void;
  onResultsChange?: (files: FileMetadata[]) => void;
}

export default function FileSearch({ userId, onFileSelect, onResultsChange }: FileSearchProps) {
  const [query, setQuery] = useState('');
  const [fileType, setFileType] = useState<string>('');
  const [results, setResults] = useState<FileMetadata[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) {
      setResults([]);
      onResultsChange?.([]);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await searchFiles({
        query: query.trim(),
        user_id: userId,
        file_type: fileType || undefined,
        limit: 50,
      });

      if (response.success && response.data) {
        setResults(response.data.files);
        onResultsChange?.(response.data.files);
      } else {
        setError('搜索失敗');
        setResults([]);
        onResultsChange?.([]);
      }
    } catch (err: any) {
      setError(err.message || '搜索失敗');
      setResults([]);
      onResultsChange?.([]);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery('');
    setResults([]);
    onResultsChange?.([]);
    setError(null);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="p-4">
      <div className="flex gap-2 mb-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <input
            type="text"
            placeholder="搜索文件名、描述或標籤..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="w-full pl-10 pr-10 py-2 border rounded-lg"
          />
          {query && (
            <button
              onClick={handleClear}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <select
          value={fileType}
          onChange={(e) => setFileType(e.target.value)}
          className="px-4 py-2 border rounded-lg"
        >
          <option value="">所有類型</option>
          <option value="application/pdf">PDF</option>
          <option value="text/plain">文本</option>
          <option value="text/markdown">Markdown</option>
          <option value="application/vnd.openxmlformats-officedocument.wordprocessingml.document">Word</option>
        </select>
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      {error && (
        <div className="text-red-500 text-sm mb-2">{error}</div>
      )}

      {results.length > 0 && (
        <div className="text-sm text-gray-600 mb-2">
          找到 {results.length} 個文件
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-2">
          {results.map((file) => (
            <div
              key={file.file_id}
              onClick={() => onFileSelect?.(file)}
              className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer"
            >
              <div className="font-medium">{file.filename}</div>
              <div className="text-sm text-gray-500 mt-1">
                {file.file_type} • {file.file_size} bytes
              </div>
              {file.description && (
                <div className="text-sm text-gray-600 mt-1">{file.description}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {query && !loading && results.length === 0 && !error && (
        <div className="text-center py-8 text-gray-500">
          沒有找到匹配的文件
        </div>
      )}
    </div>
  );
}
