// 代碼功能說明：聊天搜索 Modal 組件，用於搜索聊天記錄
// 創建日期：2026-01-06
// 創建人：Daniel Chung
// 最後修改日期：2026-01-06

import { useState, useMemo } from 'react';
import { Message } from './Sidebar';
import { useLanguage } from '../contexts/languageContext';

interface ChatSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  messages: Message[];
  onSelectMessage: (messageId: string) => void;
}

interface SearchResult {
  message: Message;
  matchIndex: number;
  preview: string;
}

export default function ChatSearchModal({
  isOpen,
  onClose,
  messages,
  onSelectMessage,
}: ChatSearchModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const { t } = useLanguage();

  // 搜索邏輯
  const searchResults = useMemo(() => {
    if (!searchQuery.trim() || messages.length === 0) {
      return [];
    }

    const query = searchQuery.toLowerCase();
    const results: SearchResult[] = [];

    messages.forEach((message) => {
      const content = message.content.toLowerCase();
      const index = content.indexOf(query);

      if (index !== -1) {
        // 獲取匹配位置的預覽文本（前後各50個字符）
        const start = Math.max(0, index - 50);
        const end = Math.min(message.content.length, index + query.length + 50);
        const preview = message.content.substring(start, end);

        results.push({
          message,
          matchIndex: index,
          preview,
        });
      }
    });

    return results;
  }, [searchQuery, messages]);

  // 處理搜索結果點擊
  const handleResultClick = (messageId: string) => {
    onSelectMessage(messageId);
    onClose();
    setSearchQuery('');
  };

  // 處理 ESC 鍵關閉
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
      onKeyDown={handleKeyDown}
    >
      <div
        className="bg-secondary border border-primary rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[80vh] flex flex-col theme-transition"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="p-4 border-b border-primary flex items-center justify-between">
          <h3 className="text-base font-semibold text-primary">
            {t('chat.search.title', '搜索聊天記錄')}
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
            aria-label={t('chat.search.close', '關閉')}
          >
            <i className="fa-solid fa-times"></i>
          </button>
        </div>

        {/* Search Input */}
        <div className="p-4 border-b border-primary">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <i className="fa-solid fa-search absolute left-3 top-1/2 transform -translate-y-1/2 text-tertiary"></i>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('chat.search.placeholder', '輸入關鍵詞搜索...')}
                className="w-full pl-10 pr-4 py-2 bg-tertiary border border-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-primary text-[12.8px]"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && searchResults.length > 0) {
                    handleResultClick(searchResults[0].message.id);
                  }
                }}
              />
            </div>
            <button
              onClick={() => {
                if (searchResults.length > 0) {
                  handleResultClick(searchResults[0].message.id);
                }
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors text-[12.8px]"
              disabled={searchResults.length === 0}
            >
              {t('chat.search.search', '搜索')}
            </button>
          </div>
        </div>

        {/* Search Results */}
        <div className="flex-1 overflow-y-auto p-4">
          {searchQuery.trim() && searchResults.length === 0 ? (
            <div className="text-center py-8 text-tertiary text-[12.8px]">
              <i className="fa-solid fa-search text-2xl mb-2"></i>
              <p>{t('chat.search.noResults', '沒有找到匹配的結果')}</p>
            </div>
          ) : searchQuery.trim() ? (
            <div className="space-y-2">
              {searchResults.map((result, index) => {
                const { message, preview } = result;
                const queryLower = searchQuery.toLowerCase();
                const previewLower = preview.toLowerCase();
                const matchIndex = previewLower.indexOf(queryLower);

                // 高亮匹配的文本
                const beforeMatch = preview.substring(0, matchIndex);
                const matchText = preview.substring(matchIndex, matchIndex + searchQuery.length);
                const afterMatch = preview.substring(matchIndex + searchQuery.length);

                return (
                  <button
                    key={`${message.id}-${index}`}
                    onClick={() => handleResultClick(message.id)}
                    className="w-full text-left p-3 rounded-lg bg-tertiary hover:bg-hover transition-colors border border-primary/30 hover:border-primary/50"
                  >
                    <div className="flex items-start gap-2 mb-1">
                      <div
                        className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                          message.sender === 'ai' ? 'bg-blue-600' : 'bg-tertiary'
                        }`}
                      >
                        <i
                          className={`fa-solid ${
                            message.sender === 'ai' ? 'fa-robot' : 'fa-user'
                          } text-xs text-white`}
                        ></i>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[11.2px] text-tertiary mb-1">
                          {message.sender === 'ai'
                            ? t('chat.aiAssistant', 'AI 助手')
                            : t('chat.user', '用戶')}
                          {' • '}
                          {message.timestamp}
                        </div>
                        <div className="text-[12.8px] text-primary line-clamp-2">
                          {beforeMatch}
                          <mark className="bg-yellow-500/30 text-primary px-0.5 rounded">
                            {matchText}
                          </mark>
                          {afterMatch}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-tertiary text-[12.8px]">
              <i className="fa-solid fa-search text-2xl mb-2"></i>
              <p>{t('chat.search.enterQuery', '請輸入關鍵詞開始搜索')}</p>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        {searchResults.length > 0 && (
          <div className="p-4 border-t border-primary text-[11.2px] text-tertiary">
            {t('chat.search.resultsCount', `找到 ${searchResults.length} 條結果`)}
          </div>
        )}
      </div>
    </div>
  );
}
