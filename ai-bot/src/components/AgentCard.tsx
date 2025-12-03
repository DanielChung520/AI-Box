/**
 * Agent 卡片組件
 * 功能：顯示 Agent 信息卡片，支持編輯和刪除操作
 * 創建日期：2025-01-27
 * 創建人：Daniel Chung
 * 最後修改日期：2025-01-27
 */

import { useState, useRef, useEffect } from 'react';
import { FiMoreVertical, FiEdit2, FiTrash2 } from 'react-icons/fi';
import { cn } from '../lib/utils';
import { useTheme } from '../hooks/useTheme';
import { useLanguage } from '../contexts/languageContext';

interface AgentProps {
  agent: {
    id: string;
    name: string;
    description: string;
    icon: string;
    status: 'registering' | 'online' | 'maintenance' | 'deprecated';
    usageCount: number;
  };
}

interface AgentCardProps extends AgentProps {
  onEdit?: (agentId: string) => void;
  onDelete?: (agentId: string) => void;
}

export default function AgentCard({ agent, onEdit, onDelete }: AgentCardProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
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

  // 根据状态获取颜色和文本
  const getStatusInfo = () => {
    switch (agent.status) {
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
      'bg-secondary rounded-xl p-4 border border-primary transition-all duration-300 theme-transition',
      theme === 'light' && 'shadow-xl shadow-gray-300/80', // 增强浅色模式下的阴影效果
      isHovered ? 'border-blue-500/50 shadow-2xl shadow-blue-500/20' : ''
    )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* 卡片头部 */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-blue-900/30 rounded-lg flex items-center justify-center mr-3">
            <i className={`fa-solid ${agent.icon} text-blue-400`}></i>
          </div>
          <h3 className="font-medium text-primary">{agent.name}</h3>
        </div>
        <div className="flex items-center gap-2">
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
                    onEdit?.(agent.id);
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center gap-2 text-primary"
                >
                  <FiEdit2 size={16} className="text-blue-400" />
                  <span>{t('agent.actions.edit', '修改')}</span>
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowMenu(false);
                    if (window.confirm(t('agent.actions.confirmDelete', `確定要刪除 "${agent.name}" 嗎？`))) {
                      onDelete?.(agent.id);
                    }
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-tertiary transition-colors flex items-center gap-2 text-red-400"
                >
                  <FiTrash2 size={16} />
                  <span>{t('agent.actions.delete', '刪除')}</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 卡片内容 */}
      <p className="text-sm text-tertiary mb-4">{agent.description}</p>

      {/* 卡片底部 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center text-xs text-muted">
          <i className="fa-solid fa-chart-bar mr-1"></i>
          <span>{t('agent.usage')}{agent.usageCount}</span>
        </div>
        <button
          className={`px-3 py-1 text-sm rounded-lg transition-colors ${
            isHovered
              ? 'bg-blue-600 text-white'
              : 'bg-tertiary text-secondary hover:bg-hover'
          }`}
        >
          <i className="fa-solid fa-comment mr-1"></i>
          {t('agent.chat')}
        </button>
      </div>
    </div>
  );
}
