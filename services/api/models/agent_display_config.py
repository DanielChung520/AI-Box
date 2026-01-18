# 代碼功能說明: Agent Display Config 數據模型
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Agent Display Config 數據模型定義

用於前端代理展示區的配置管理，支持分類和代理的展示配置。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class MultilingualText(BaseModel):
    """多語言文本"""

    en: str = Field(description="英文文本")
    zh_CN: str = Field(description="簡體中文文本")
    zh_TW: str = Field(description="繁體中文文本")


class CategoryConfig(BaseModel):
    """分類配置"""

    id: str = Field(description="分類 ID（如 'human-resource'）")
    display_order: int = Field(ge=0, description="顯示順序，數字越小越靠前")
    is_visible: bool = Field(default=True, description="是否顯示")
    name: MultilingualText = Field(description="多語言名稱")
    icon: Optional[str] = Field(default=None, description="分類圖標（可選）")
    description: Optional[MultilingualText] = Field(default=None, description="多語言描述（可選）")


class AgentConfig(BaseModel):
    """代理配置"""

    id: str = Field(description="代理 ID（如 'hr-1'）")
    category_id: str = Field(description="所屬分類 ID")
    display_order: int = Field(ge=0, description="在分類中的顯示順序")
    is_visible: bool = Field(default=True, description="是否顯示")
    name: MultilingualText = Field(description="多語言名稱")
    description: MultilingualText = Field(description="多語言描述")
    icon: str = Field(description="圖標類名（如 'fa-user-tie'）")
    status: str = Field(
        default="online",
        pattern="^(registering|online|maintenance|deprecated)$",
        description="狀態：registering/online/maintenance/deprecated",
    )
    usage_count: Optional[int] = Field(default=None, ge=0, description="使用次數（可選，可從實際使用統計獲取）")
    agent_id: Optional[str] = Field(default=None, description="實際的 Agent ID（用於關聯註冊的 Agent）")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="額外元數據（可選）")

    # ============================================
    # 技術配置字段（用於 Agent Registry 註冊）
    # ============================================
    agent_type: Optional[str] = Field(
        default="execution",
        pattern="^(execution|planning|review)$",
        description="Agent 類型：execution（執行）/planning（規劃）/review（審查）",
    )
    protocol: Optional[str] = Field(
        default="http",
        pattern="^(http|mcp)$",
        description="通信協議：http/mcp",
    )
    endpoint_url: Optional[str] = Field(
        default=None,
        description="Agent 端點 URL（HTTP 或 MCP endpoint）",
    )
    secret_id: Optional[str] = Field(
        default=None,
        description="Secret ID（由 AI-Box 簽發，用於外部 Agent 身份驗證）",
    )
    secret_key: Optional[str] = Field(
        default=None,
        description="Secret Key（用於外部 Agent 認證）",
    )

    # ============================================
    # 預留字段（下個迭代使用）
    # ============================================
    capabilities: Optional[list[str]] = Field(
        default=None,
        description="能力列表（預留，下個迭代使用）",
    )
    permission_groups: Optional[list[str]] = Field(
        default=None,
        description="權限組列表（預留，下個迭代使用）",
    )
    tool_calls: Optional[list[str]] = Field(
        default=None,
        description="工具調用列表（預留，下個迭代使用）",
    )


class AgentDisplayConfigModel(BaseModel):
    """代理展示配置模型（ArangoDB 文檔格式）"""

    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(alias="_key", description="文檔唯一標識")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID（null 表示系統級）")
    config_type: str = Field(pattern="^(category|agent)$", description="配置類型：category 或 agent")
    category_id: Optional[str] = Field(default=None, description="分類 ID（category 類型時使用）")
    agent_id: Optional[str] = Field(default=None, description="代理 ID（agent 類型時使用）")
    category_config: Optional[CategoryConfig] = Field(
        default=None, description="分類配置（config_type = 'category' 時）"
    )
    agent_config: Optional[AgentConfig] = Field(
        default=None, description="代理配置（config_type = 'agent' 時）"
    )
    is_active: bool = Field(default=True, description="是否啟用")
    created_at: str = Field(description="創建時間（ISO 8601 格式）")
    updated_at: str = Field(description="更新時間（ISO 8601 格式）")
    created_by: Optional[str] = Field(default=None, description="創建人")
    updated_by: Optional[str] = Field(default=None, description="更新人")
