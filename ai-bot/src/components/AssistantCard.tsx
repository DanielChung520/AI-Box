/**
 * Assistant 卡片組件
 * 功能：顯示 Assistant 信息卡片，支持維護操作
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2025-01-27
 */

import { useState, useRef, useEffect } from 'react';
import { FiMoreVertical, FiEdit2, FiTrash2 } from 'react-icons/fi';
import { FaHeart, FaRegHeart } from 'react-icons/fa';
import { cn } from '../lib/utils';
import { useTheme } from '../hooks/useTheme';
import { useLanguage } from '../contexts/languageContext';

interface AssistantProps {
  assistant: {
    id: string;
    name: string;
    description: string;
    icon: string;
    status: 'registering' | 'online' | 'maintenance' | 'deprecated';
    usageCount: number;
  };
}

interface AssistantCardProps extends AssistantProps {
  onEdit?: (assistantId: string) => void;
  onDelete?: (assistantId: string) => void;
  onClick?: () => void;
  onFavorite?: (assistantId: string, isFavorite: boolean) => void;
  isFavorite?: boolean;
}

export default function AssistantCard({ assistant, onEdit, onDelete, onClick, onFavorite, isFavorite: initialIsFavorite = false }: AssistantCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isFavorite, setIsFavorite] = useState(initialIsFavorite);
  const menuRef = useRef<HTMLDivElement>(null);
  const { theme } = useTheme();
  const { t } = useLanguage();

  // 點擊外部區域關閉菜單
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowMenu(false);
      }
    };

    if (showMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showMenu]);

  // 根據狀態獲取顏色和文本
  const getStatusInfo = () => {
    switch (assistant.status) {
      case 'registering':
        return { color: 'bg-gray-500', text: t('agent.status.registering', '註冊中') };
      case 'online':
        return { color: 'bg-green-500', text: t('agent.status.online', '在線') };
      case 'maintenance':
        return { color: 'bg-yellow-500', text: t('agent.status.maintenance', '維修中') };
      case 'deprecated':
        return { color: 'bg-red-500', text: t('agent.status.deprecated', '已作廢') };
      default:
        return { color: 'bg-gray-500', text: '未知' };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div
      className={cn(
        'rounded-xl p-4 border transition-all duration-300 theme-transition cursor-pointer assistant-card',
        theme === 'light' && 'bg-secondary shadow-xl shadow-gray-300/80 border-primary',
        theme === 'blue-light' && '',
        theme === 'dark' && 'bg-secondary border-primary',
        isHovered ? 'border-purple-500/50 shadow-2xl shadow-purple-500/20' : ''
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* 卡片頭部 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center mr-3">
            <i className={`fa-solid ${assistant.icon} text-purple-600 dark:text-purple-400`}></i>
          </div>
          <h3 className="font-medium text-primary">{assistant.name}</h3>
        </div>
        <div className="flex items-center gap-2">
          {/* 收藏圖標 */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              const newFavoriteState = !isFavorite;
              setIsFavorite(newFavoriteState);
              onFavorite?.(assistant.id, newFavoriteState);
            }}
            className="p-1.5 rounded-lg hover:bg-tertiary transition-colors"
            title={isFavorite ? t('assistant.favorite.remove', '取消收藏') : t('assistant.favorite.add', '加入收藏')}
          >
            {isFavorite ? (
              <FaHeart
                size={18}
                className="text-yellow-400"
              />
            ) : (
              <FaRegHeart
                size={18}
                className="text-gray-400 hover:text-yellow-400 transition-colors"
              />
            )}
          </button>

          <span className={`text-xs px-2 py-0.5 rounded-full ${statusInfo.color} text-white`}>
            {statusInfo.text}
          </span>

          {/* 更多操作按鈕 */}
          <div className="relative" ref={menuRef}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowMenu(!showMenu);
              }}
              className="p-1.5 rounded-lg hover:bg-tertiary transition-colors text-tertiary hover:text-primary"
              title="更多操作"
            >
              <FiMoreVertical size={18} />
            </button>

            {/* 下拉菜單 */}
            {showMenu && (
              <div className="absolute right-0 top-full mt-1 w-36 bg-secondary border border-primary rounded-lg shadow-lg z-10 theme-transition">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onEdit?.(assistant.id);
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center gap-2 text-primary"
                >
                  <FiEdit2 size={16} className="text-blue-400" />
                  <span>{t('assistant.actions.edit', '編輯')}</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    onDelete?.(assistant.id);
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center gap-2 text-red-400"
                >
                  <FiTrash2 size={16} className="text-red-400" />
                  <span>{t('assistant.actions.delete', '刪除')}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 卡片內容 */}
      <p className="text-sm text-tertiary mb-4">{assistant.description}</p>

      {/* 卡片底部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center text-xs text-muted">
          <i className="fa-solid fa-chart-bar mr-1"></i>
          <span>{t('agent.usage', '使用次數：')}{assistant.usageCount}</span>
        </div>
        <button
          className={`px-3 py-1 text-sm rounded-lg transition-colors ${
            isHovered
              ? 'bg-purple-600 text-white'
              : 'bg-tertiary text-secondary hover:bg-hover'
          }`}
        >
          <i className="fa-solid fa-comment mr-1"></i>
          {t('agent.chat', '聊天')}
        </button>
      </div>
    </div>
  );
}
