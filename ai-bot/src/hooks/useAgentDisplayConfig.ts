// 代碼功能說明: Agent Display Config Hook
// 創建日期: 2026-01-13
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-13

/**
 * Agent Display Config Hook
 * 用於從後端獲取代理展示配置並轉換為前端使用的格式
 */

import { useState, useEffect, useMemo } from 'react';
import { getAgentDisplayConfig } from '../lib/api';
import { useLanguage } from '../contexts/languageContext';
import type { AgentDisplayConfigResponse, CategoryWithAgents } from '../types/agentDisplayConfig';

// 前端使用的格式（與 ChatArea.tsx 中的接口保持一致）
export interface AgentCategory {
  id: string;
  name: string;
  agents: Agent[];
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  icon: string;
  status: 'registering' | 'online' | 'maintenance' | 'deprecated';
  usageCount: number;
}

export function useAgentDisplayConfig(tenantId?: string) {
  const { language } = useLanguage();
  const [config, setConfig] = useState<AgentDisplayConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    async function fetchConfig() {
      try {
        setLoading(true);
        setError(null);
        const data = await getAgentDisplayConfig(tenantId, false);
        setConfig(data);
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to load agent display config');
        setError(error);
        console.error('Failed to load agent display config:', error);
        // 設置為 null，讓組件可以處理錯誤情況
        setConfig(null);
      } finally {
        setLoading(false);
      }
    }

    fetchConfig();
  }, [tenantId]);

  // 轉換為前端使用的格式
  const agentCategories: AgentCategory[] = useMemo(() => {
    if (!config || !config.categories) {
      return [];
    }

    // 獲取多語言文本（在 useMemo 內部定義，避免依賴問題）
    const getText = (text: { en: string; zh_CN: string; zh_TW: string }): string => {
      if (!text) {
        return '';
      }
      switch (language) {
        case 'zh_CN':
          return text.zh_CN || text.en || '';
        case 'zh_TW':
          return text.zh_TW || text.en || '';
        default:
          return text.en || '';
      }
    };

    try {
      return config.categories
        .filter(cat => cat && cat.is_visible)
        .sort((a, b) => a.display_order - b.display_order)
        .map(category => ({
          id: category.id,
          name: getText(category.name),
          agents: (category.agents || [])
            .filter(agent => agent && agent.is_visible)
            .sort((a, b) => a.display_order - b.display_order)
            .map(agent => ({
              id: agent.id,
              name: getText(agent.name),
              description: getText(agent.description),
              icon: agent.icon || '',
              status: (agent.status || 'online') as 'registering' | 'online' | 'maintenance' | 'deprecated',
              usageCount: agent.usage_count || 0,
            })),
        }));
    } catch (err) {
      console.error('Error processing agent categories:', err);
      return [];
    }
  }, [config, language]);

  // 刷新配置
  const refetch = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAgentDisplayConfig(tenantId, false);
      setConfig(data);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to load agent display config');
      setError(error);
      console.error('Failed to refetch agent display config:', error);
    } finally {
      setLoading(false);
    }
  };

  return {
    config,
    agentCategories,
    loading,
    error,
    refetch,
  };
}
