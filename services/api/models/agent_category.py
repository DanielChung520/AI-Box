# 代碼功能說明: Agent Category 數據模型
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Agent Category 數據模型定義

用於管理代理分類（如人力資源、物流、財務、生產管理等），由系統管理員管理。
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from services.api.models.agent_display_config import MultilingualText


class AgentCategory(BaseModel):
    """代理分類模型"""

    id: str = Field(description="分類 ID（如 'human-resource'）")
    display_order: int = Field(ge=0, description="顯示順序，數字越小越靠前")
    is_visible: bool = Field(default=True, description="是否顯示")
    name: MultilingualText = Field(description="多語言名稱")
    icon: Optional[str] = Field(default=None, description="分類圖標（FontAwesome 類名，如 'fa-users'）")
    description: Optional[MultilingualText] = Field(default=None, description="多語言描述（可選）")


class AgentCategoryDocument(BaseModel):
    """代理分類 ArangoDB 文檔模型"""

    key: str = Field(alias="_key", description="文檔唯一標識（分類 ID）")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID（null 表示系統級）")
    category: AgentCategory = Field(description="分類配置")
    is_active: bool = Field(default=True, description="是否啟用（軟刪除標記）")
    created_at: str = Field(description="創建時間（ISO 8601 格式）")
    updated_at: str = Field(description="更新時間（ISO 8601 格式）")
    created_by: Optional[str] = Field(default=None, description="創建人（系統管理員）")
    updated_by: Optional[str] = Field(default=None, description="更新人（系統管理員）")
