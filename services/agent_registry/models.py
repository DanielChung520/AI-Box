# 代碼功能說明: Agent Registry 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry 數據模型定義"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class AgentPermission(str, Enum):
    """Agent 權限類型"""

    PUBLIC = "public"  # 公開，所有人可用
    AUTHENTICATED = "authenticated"  # 已認證用戶可用
    ROLE_BASED = "role_based"  # 基於角色的權限
    USER_SPECIFIC = "user_specific"  # 特定用戶


class AgentStatus(str, Enum):
    """Agent 狀態"""

    ACTIVE = "active"  # 活躍
    INACTIVE = "inactive"  # 非活躍
    PENDING = "pending"  # 待審核
    SUSPENDED = "suspended"  # 已暫停
    OFFLINE = "offline"  # 離線


class AgentPermissionConfig(BaseModel):
    """Agent 權限配置"""

    permission_type: AgentPermission = Field(
        default=AgentPermission.PUBLIC, description="權限類型"
    )
    allowed_roles: Optional[List[str]] = Field(
        default=None, description="允許的角色列表（role_based 時使用）"
    )
    allowed_users: Optional[List[str]] = Field(
        default=None, description="允許的用戶列表（user_specific 時使用）"
    )


class AgentEndpoints(BaseModel):
    """Agent 端點配置"""

    mcp_endpoint: str = Field(..., description="MCP 協議端點 URL")
    health_endpoint: str = Field(..., description="健康檢查端點 URL")
    execute_endpoint: Optional[str] = Field(default=None, description="任務執行端點 URL（可選）")


class AgentMetadata(BaseModel):
    """Agent 完整元數據"""

    name: str = Field(..., description="Agent 名稱")
    description: str = Field(..., description="Agent 描述")
    purpose: str = Field(..., description="Agent 用途說明")
    category: str = Field(..., description="Agent 分類")
    version: str = Field(default="1.0.0", description="Agent 版本")
    developer: Optional[str] = Field(default=None, description="開發者信息")
    icon_url: Optional[str] = Field(default=None, description="圖標 URL")
    documentation_url: Optional[str] = Field(default=None, description="文檔 URL")
    support_url: Optional[str] = Field(default=None, description="支持 URL")
    tags: List[str] = Field(default_factory=list, description="標籤列表")


class AgentRegistryInfo(BaseModel):
    """Agent Registry 信息模型（完整的 Agent 元數據）"""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型")
    status: AgentStatus = Field(default=AgentStatus.PENDING, description="Agent 狀態")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: AgentMetadata = Field(..., description="Agent 元數據")
    endpoints: AgentEndpoints = Field(..., description="Agent 端點配置")
    permissions: AgentPermissionConfig = Field(
        default_factory=lambda: AgentPermissionConfig(),
        description="權限配置",
    )
    registered_at: datetime = Field(default_factory=datetime.now, description="註冊時間")
    last_heartbeat: Optional[datetime] = Field(None, description="最後心跳時間")
    last_updated: datetime = Field(default_factory=datetime.now, description="最後更新時間")
    extra: Dict[str, Any] = Field(default_factory=dict, description="額外信息")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AgentRegistrationRequest(BaseModel):
    """Agent 註冊請求模型"""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: AgentMetadata = Field(..., description="Agent 元數據")
    endpoints: AgentEndpoints = Field(..., description="Agent 端點配置")
    permissions: Optional[AgentPermissionConfig] = Field(
        default=None, description="權限配置"
    )
    extra: Optional[Dict[str, Any]] = Field(default=None, description="額外信息")
