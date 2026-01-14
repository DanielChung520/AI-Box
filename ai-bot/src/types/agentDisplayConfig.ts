// 代碼功能說明: Agent Display Config 類型定義
// 創建日期: 2026-01-13
// 創建人: Daniel Chung
// 最後修改日期: 2026-01-13

/**
 * Agent Display Config 類型定義
 * 用於前端代理展示區的配置管理
 */

export interface MultilingualText {
  en: string;
  zh_CN: string;
  zh_TW: string;
}

export interface CategoryConfig {
  id: string;
  display_order: number;
  is_visible: boolean;
  name: MultilingualText;
  icon?: string;
  description?: MultilingualText;
}

export interface AgentConfig {
  id: string;
  category_id: string;
  display_order: number;
  is_visible: boolean;
  name: MultilingualText;
  description: MultilingualText;
  icon: string;
  status: 'registering' | 'online' | 'maintenance' | 'deprecated';
  usage_count?: number;
  agent_id?: string;
  metadata?: Record<string, any>;
}

export interface CategoryWithAgents extends CategoryConfig {
  agents: AgentConfig[];
}

export interface AgentDisplayConfigResponse {
  categories: CategoryWithAgents[];
}
