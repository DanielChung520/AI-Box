// 代碼功能說明：聊天搜索 Modal 組件，用於搜索聊天記錄
// 創建日期：2026-01-06
// 創建人：Daniel Chung
// 最後修改日期：2026-01-16

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

type DateFilterType = 'all' | 'today' | 'yesterday' | '7days' | '30days' | 'custom';

// 日期工具函数
const parseTimestamp = (timestamp: string): Date | null => {
  if (!timestamp) return null;

  // 尝试 ISO 8601 格式
  const isoDate = new Date(timestamp);
  if (!isNaN(isoDate.getTime())) {
    return isoDate;
  }

  // 尝试本地化格式（如 "2026/1/16 下午3:30" 或 "2026-01-16 15:30"）
  // 移除可能的本地化标记
  const cleaned = timestamp.replace(/[上午下午]/g, '').trim();
  const localDate = new Date(cleaned);
  if (!isNaN(localDate.getTime())) {
    return localDate;
  }

  return null;
};

// 获取一天的开始时间（00:00:00）
const startOfDay = (date: Date): Date => {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
};

// 获取一天的结束时间（23:59:59.999）
const endOfDay = (date: Date): Date => {
  const d = new Date(date);
  d.setHours(23, 59, 59, 999);
  return d;
};

// 获取日期范围
const getDateRange = (
  type: DateFilterType,
  customStartDate?: string,
  customEndDate?: string
): { start: Date; end: Date } | null => {
  const now = new Date();

  switch (type) {
    case 'today':
      return {
        start: startOfDay(now),
        end: now,
      };
    case 'yesterday': {
      const yesterday = new Date(now);
      yesterday.setDate(yesterday.getDate() - 1);
      return {
        start: startOfDay(yesterday),
        end: endOfDay(yesterday),
      };
    }
    case '7days': {
      const sevenDaysAgo = new Date(now);
      sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
      return {
        start: startOfDay(sevenDaysAgo),
        end: now,
      };
    }
    case '30days': {
      const thirtyDaysAgo = new Date(now);
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
      return {
        start: startOfDay(thirtyDaysAgo),
        end: now,
      };
    }
    case 'custom': {
      if (!customStartDate || !customEndDate) {
        return null;
      }
      const start = startOfDay(new Date(customStartDate));
      const end = endOfDay(new Date(customEndDate));
      return { start, end };
    }
    case 'all':
    default:
      return null; // 全部时间，不进行日期过滤
  }
};

// 格式化日期为 YYYY-MM-DD（用于 input type="date"）
const formatDateForInput = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

export default function ChatSearchModal({
  isOpen,
  onClose,
  messages,
  onSelectMessage,
}: ChatSearchModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilterType, setDateFilterType] = useState<DateFilterType>('all');
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');
  const [dateRangeError, setDateRangeError] = useState<string>('');
  const { t } = useLanguage();

  // 日期范围验证
  const validateDateRange = (): boolean => {
    if (dateFilterType !== 'custom') {
      setDateRangeError('');
      return true;
    }

    if (!customStartDate || !customEndDate) {
      setDateRangeError(t('chat.search.dateRange.incomplete', '請選擇完整的日期範圍'));
      return false;
    }

    const start = new Date(customStartDate);
    const end = new Date(customEndDate);

    if (start > end) {
      setDateRangeError(t('chat.search.dateRange.invalid', '起始日期不能晚於結束日期'));
      return false;
    }

    setDateRangeError('');
    return true;
  };

  // 搜索邏輯
  const searchResults = useMemo(() => {
    if (messages.length === 0) {
      return [];
    }

    // 验证日期范围
    if (!validateDateRange()) {
      return [];
    }

    let filteredMessages = messages;

    // 1. 日期过滤
    if (dateFilterType !== 'all') {
      const dateRange = getDateRange(dateFilterType, customStartDate, customEndDate);
      if (dateRange) {
        filteredMessages = filteredMessages.filter((message) => {
          const msgDate = parseTimestamp(message.timestamp);
          if (!msgDate) return false;
          return msgDate >= dateRange.start && msgDate <= dateRange.end;
        });
      }
    }

    // 2. 关键词过滤（如果有关键词）
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filteredMessages = filteredMessages.filter((message) => {
        return message.content.toLowerCase().includes(query);
      });
    }

    // 3. 生成搜索结果（包含预览和高亮）
    const results: SearchResult[] = [];
    const query = searchQuery.toLowerCase();

    filteredMessages.forEach((message) => {
      let matchIndex = 0;
      let preview = message.content;

      // 如果有关键词，生成预览和高亮位置
      if (query) {
        const content = message.content.toLowerCase();
        matchIndex = content.indexOf(query);
        if (matchIndex !== -1) {
          // 獲取匹配位置的預覽文本（前後各50個字符）
          const start = Math.max(0, matchIndex - 50);
          const end = Math.min(message.content.length, matchIndex + query.length + 50);
          preview = message.content.substring(start, end);
        }
      } else {
        // 没有关键词时，显示消息的前100个字符作为预览
        preview = message.content.substring(0, 100);
        if (message.content.length > 100) {
          preview += '...';
        }
      }

      results.push({
        message,
        matchIndex: query ? matchIndex : 0,
        preview,
      });
    });

    // 4. 按时间倒序排序（最新的在前）
    results.sort((a, b) => {
      const dateA = parseTimestamp(a.message.timestamp);
      const dateB = parseTimestamp(b.message.timestamp);
      if (!dateA || !dateB) return 0;
      return dateB.getTime() - dateA.getTime();
    });

    return results;
  }, [searchQuery, messages, dateFilterType, customStartDate, customEndDate, t]);

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

        {/* Date Filter Section */}
        <div className="p-4 border-b border-primary">
          {/* Quick Date Filter Buttons */}
          <div className="flex flex-wrap gap-2 mb-3">
            <button
              onClick={() => {
                setDateFilterType('all');
                setCustomStartDate('');
                setCustomEndDate('');
                setDateRangeError('');
              }}
              className={`px-3 py-1.5 rounded-lg text-[11.2px] transition-colors ${
                dateFilterType === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-hover'
              }`}
            >
              {t('chat.search.dateFilter.all', '全部時間')}
            </button>
            <button
              onClick={() => {
                setDateFilterType('today');
                setCustomStartDate('');
                setCustomEndDate('');
                setDateRangeError('');
              }}
              className={`px-3 py-1.5 rounded-lg text-[11.2px] transition-colors ${
                dateFilterType === 'today'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-hover'
              }`}
            >
              {t('chat.search.dateFilter.today', '今天')}
            </button>
            <button
              onClick={() => {
                setDateFilterType('yesterday');
                setCustomStartDate('');
                setCustomEndDate('');
                setDateRangeError('');
              }}
              className={`px-3 py-1.5 rounded-lg text-[11.2px] transition-colors ${
                dateFilterType === 'yesterday'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-hover'
              }`}
            >
              {t('chat.search.dateFilter.yesterday', '昨天')}
            </button>
            <button
              onClick={() => {
                setDateFilterType('7days');
                setCustomStartDate('');
                setCustomEndDate('');
                setDateRangeError('');
              }}
              className={`px-3 py-1.5 rounded-lg text-[11.2px] transition-colors ${
                dateFilterType === '7days'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-hover'
              }`}
            >
              {t('chat.search.dateFilter.7days', '最近 7 天')}
            </button>
            <button
              onClick={() => {
                setDateFilterType('30days');
                setCustomStartDate('');
                setCustomEndDate('');
                setDateRangeError('');
              }}
              className={`px-3 py-1.5 rounded-lg text-[11.2px] transition-colors ${
                dateFilterType === '30days'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-hover'
              }`}
            >
              {t('chat.search.dateFilter.30days', '最近 30 天')}
            </button>
            <button
              onClick={() => {
                setDateFilterType('custom');
                if (!customStartDate && !customEndDate) {
                  // 默认设置为最近7天的范围
                  const end = new Date();
                  const start = new Date();
                  start.setDate(start.getDate() - 7);
                  setCustomStartDate(formatDateForInput(start));
                  setCustomEndDate(formatDateForInput(end));
                }
              }}
              className={`px-3 py-1.5 rounded-lg text-[11.2px] transition-colors ${
                dateFilterType === 'custom'
                  ? 'bg-blue-600 text-white'
                  : 'bg-tertiary text-primary hover:bg-hover'
              }`}
            >
              {t('chat.search.dateFilter.custom', '自定義')}
            </button>
          </div>

          {/* Custom Date Range Picker */}
          {dateFilterType === 'custom' && (
            <div className="mb-3">
              <div className="flex gap-2 items-center">
                <div className="flex-1">
                  <label className="block text-[11.2px] text-tertiary mb-1">
                    {t('chat.search.dateRange.start', '起始日期')}
                  </label>
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => {
                      setCustomStartDate(e.target.value);
                      setDateRangeError('');
                    }}
                    className="w-full px-3 py-2 bg-tertiary border border-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-primary text-[12.8px]"
                  />
                </div>
                <div className="pt-6 px-2 text-tertiary text-[12.8px]">
                  {t('chat.search.dateRange.to', '至')}
                </div>
                <div className="flex-1">
                  <label className="block text-[11.2px] text-tertiary mb-1">
                    {t('chat.search.dateRange.end', '結束日期')}
                  </label>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => {
                      setCustomEndDate(e.target.value);
                      setDateRangeError('');
                    }}
                    className="w-full px-3 py-2 bg-tertiary border border-primary rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-primary text-[12.8px]"
                  />
                </div>
              </div>
              {dateRangeError && (
                <div className="mt-2 text-[11.2px] text-red-500">{dateRangeError}</div>
              )}
            </div>
          )}

          {/* Search Input */}
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
          {(() => {
            const hasDateFilter = dateFilterType !== 'all';
            const hasKeyword = searchQuery.trim().length > 0;
            const hasResults = searchResults.length > 0;

            // 空状态：没有任何筛选条件
            if (!hasDateFilter && !hasKeyword) {
              return (
                <div className="text-center py-8 text-tertiary text-[12.8px]">
                  <i className="fa-solid fa-search text-2xl mb-2"></i>
                  <p>{t('chat.search.enterQuery', '請輸入關鍵詞或選擇日期範圍開始搜索')}</p>
                </div>
              );
            }

            // 空状态：有筛选条件但没有结果
            if (!hasResults) {
              return (
                <div className="text-center py-8 text-tertiary text-[12.8px]">
                  <i className="fa-solid fa-search text-2xl mb-2"></i>
                  <p>{t('chat.search.noResults', '沒有找到匹配的結果')}</p>
                  {(hasDateFilter || hasKeyword) && (
                    <p className="mt-2 text-[11.2px]">
                      {t('chat.search.tryDifferent', '請嘗試調整日期範圍或關鍵詞')}
                    </p>
                  )}
                </div>
              );
            }

            // 显示搜索结果
            return (
              <div className="space-y-2">
                {searchResults.map((result, index) => {
                  const { message, preview } = result;
                  const queryLower = searchQuery.toLowerCase();
                  const previewLower = preview.toLowerCase();
                  const matchIndex = previewLower.indexOf(queryLower);

                  // 格式化时间戳显示
                  const formatTimestamp = (timestamp: string): string => {
                    const date = parseTimestamp(timestamp);
                    if (!date) return timestamp; // 如果解析失败，返回原始值

                    const now = new Date();
                    const today = startOfDay(now);
                    const yesterday = new Date(today);
                    yesterday.setDate(yesterday.getDate() - 1);

                    const msgDate = startOfDay(date);

                    // 今天：显示时间
                    if (msgDate.getTime() === today.getTime()) {
                      return date.toLocaleTimeString('zh-TW', {
                        hour: '2-digit',
                        minute: '2-digit',
                      });
                    }

                    // 昨天：显示"昨天 时间"
                    if (msgDate.getTime() === yesterday.getTime()) {
                      return `${t('chat.search.dateFilter.yesterday', '昨天')} ${date.toLocaleTimeString('zh-TW', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}`;
                    }

                    // 其他：显示完整日期和时间
                    return date.toLocaleString('zh-TW', {
                      year: 'numeric',
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    });
                  };

                  // 高亮匹配的文本（如果有关键词）
                  const renderPreview = () => {
                    if (!hasKeyword || matchIndex === -1) {
                      return <span>{preview}</span>;
                    }

                    const beforeMatch = preview.substring(0, matchIndex);
                    const matchText = preview.substring(matchIndex, matchIndex + searchQuery.length);
                    const afterMatch = preview.substring(matchIndex + searchQuery.length);

                    return (
                      <>
                        {beforeMatch}
                        <mark className="bg-yellow-500/30 text-primary px-0.5 rounded">
                          {matchText}
                        </mark>
                        {afterMatch}
                      </>
                    );
                  };

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
                            {formatTimestamp(message.timestamp)}
                          </div>
                          <div className="text-[12.8px] text-primary line-clamp-2">
                            {renderPreview()}
                          </div>
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            );
          })()}
        </div>

        {/* Modal Footer */}
        {searchResults.length > 0 && (
          <div className="p-4 border-t border-primary text-[11.2px] text-tertiary">
            <div className="flex items-center justify-between">
              <span>
                {t('chat.search.resultsCount', `找到 ${searchResults.length} 條結果`).replace('{count}', String(searchResults.length))}
              </span>
              {dateFilterType !== 'all' && (
                <span className="text-[10.4px]">
                  {(() => {
                    const dateRange = getDateRange(dateFilterType, customStartDate, customEndDate);
                    if (!dateRange) return '';

                    if (dateFilterType === 'custom') {
                      return `${customStartDate} ${t('chat.search.dateRange.to', '至')} ${customEndDate}`;
                    }

                    const formatDate = (date: Date) => {
                      return date.toLocaleDateString('zh-TW', {
                        year: 'numeric',
                        month: '2-digit',
                        day: '2-digit',
                      });
                    };

                    return `${formatDate(dateRange.start)} ${t('chat.search.dateRange.to', '至')} ${formatDate(dateRange.end)}`;
                  })()}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
