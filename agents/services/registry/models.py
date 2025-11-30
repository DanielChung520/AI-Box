# 代碼功能說明: Agent Registry 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry 數據模型定義"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from agents.services.protocol.base import AgentServiceProtocolType


class AgentPermission(str, Enum):
    """Agent 權限類型"""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class AgentStatus(str, Enum):
    """Agent 狀態"""

    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"


class AgentPermissionConfig(BaseModel):
    """Agent 權限配置"""

    read: bool = True
    write: bool = False
    execute: bool = True
    admin: bool = False


class AgentEndpoints(BaseModel):
    """Agent 端點配置"""

    http: Optional[str] = Field(None, description="HTTP 端點 URL")
    mcp: Optional[str] = Field(None, description="MCP 端點 URL")
    protocol: AgentServiceProtocolType = Field(
        AgentServiceProtocolType.HTTP, description="默認協議類型"
    )


class AgentMetadata(BaseModel):
    """Agent 元數據"""

    version: str = Field("1.0.0", description="Agent 版本")
    description: Optional[str] = Field(None, description="Agent 描述")
    author: Optional[str] = Field(None, description="開發者/團隊")
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="能力描述")


class AgentRegistryInfo(BaseModel):
    """Agent Registry 信息"""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型（planning/execution/review）")
    name: str = Field(..., description="Agent 名稱")
    status: AgentStatus = Field(AgentStatus.OFFLINE, description="Agent 狀態")
    endpoints: AgentEndpoints = Field(..., description="Agent 端點配置")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: AgentMetadata = Field(default_factory=AgentMetadata, description="元數據")
    permissions: AgentPermissionConfig = Field(
        default_factory=lambda: AgentPermissionConfig(), description="權限配置"
    )
    registered_at: datetime = Field(default_factory=datetime.now, description="註冊時間")
    last_heartbeat: Optional[datetime] = Field(None, description="最後心跳時間")
    load: int = Field(0, description="當前負載")


class AgentRegistrationRequest(BaseModel):
    """Agent 註冊請求"""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型")
    name: str = Field(..., description="Agent 名稱")
    endpoints: AgentEndpoints = Field(..., description="Agent 端點配置")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: Optional[AgentMetadata] = Field(None, description="元數據")
    permissions: Optional[AgentPermissionConfig] = Field(None, description="權限配置")
