# 代碼功能說明: Agent Registry 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry 數據模型定義"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents.services.protocol.base import AgentServiceProtocolType


class AgentPermission(str, Enum):
    """Agent 權限類型"""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


class AgentStatus(str, Enum):
    """Agent 生命週期狀態

    狀態說明：
    - REGISTERING: 註冊中，等待管理單位核准
    - ONLINE: 在線，可以正常使用
    - MAINTENANCE: 維修中，暫時無法接受新任務
    - DEPRECATED: 已作廢，不再使用
    - OFFLINE: 離線（健康檢查/心跳超時標記）

    相容性別名：
    - ACTIVE: 舊版代碼使用 ACTIVE 表示「可用」，等同於 ONLINE
    - PENDING: 舊版代碼使用 PENDING 表示「等待中」，等同於 REGISTERING
    """

    REGISTERING = "registering"  # 註冊中
    ONLINE = "online"  # 在線
    MAINTENANCE = "maintenance"  # 維修中
    DEPRECATED = "deprecated"  # 已作廢
    OFFLINE = "offline"  # 離線（健康檢查標記）

    # 兼容舊代碼：使用同值 alias，避免 AttributeError
    ACTIVE = "online"
    PENDING = "registering"
    # 兼容舊代碼：添加 INACTIVE 和 SUSPENDED 別名
    INACTIVE = "offline"  # 非活躍狀態等同於離線
    SUSPENDED = "offline"  # 暫停狀態等同於離線
    # 兼容舊代碼：添加 IDLE 和 BUSY 別名
    IDLE = "online"  # 空閒狀態等同於在線
    BUSY = "maintenance"  # 忙碌狀態等同於維修中（暫時無法接受新任務）


class AgentPermissionConfig(BaseModel):
    """Agent 權限配置"""

    read: bool = True
    write: bool = False
    execute: bool = True
    admin: bool = False

    # 資源訪問權限配置（用於外部 Agent）
    allowed_memory_namespaces: List[str] = Field(
        default_factory=list, description="允許訪問的 Memory 命名空間列表"
    )
    allowed_tools: List[str] = Field(default_factory=list, description="允許使用的工具列表")
    allowed_llm_providers: List[str] = Field(
        default_factory=list, description="允許使用的 LLM Provider 列表"
    )
    allowed_databases: List[str] = Field(default_factory=list, description="允許訪問的數據庫列表")
    allowed_file_paths: List[str] = Field(default_factory=list, description="允許訪問的文件路徑列表")

    # 外部 Agent 認證配置
    secret_id: Optional[str] = Field(None, description="Secret ID（由 AI-Box 簽發，用於外部 Agent 身份驗證）")
    api_key: Optional[str] = Field(None, description="API Key（用於外部 Agent 認證）")
    server_certificate: Optional[str] = Field(None, description="服務器證書（用於 mTLS 認證）")
    ip_whitelist: List[str] = Field(default_factory=list, description="IP 白名單列表")
    server_fingerprint: Optional[str] = Field(None, description="服務器指紋（用於身份驗證）")


class AgentEndpoints(BaseModel):
    """Agent 端點配置"""

    http: Optional[str] = Field(None, description="HTTP 端點 URL")
    mcp: Optional[str] = Field(None, description="MCP 端點 URL")
    protocol: AgentServiceProtocolType = Field(AgentServiceProtocolType.HTTP, description="默認協議類型")
    is_internal: bool = Field(False, description="是否為內部 Agent")

    # 兼容舊代碼：添加別名屬性
    @property
    def mcp_endpoint(self) -> Optional[str]:
        """MCP 端點 URL（兼容舊代碼）"""
        return self.mcp

    @property
    def health_endpoint(self) -> Optional[str]:
        """健康檢查端點 URL（兼容舊代碼，使用 HTTP 端點）"""
        return self.http


class AgentMetadata(BaseModel):
    """Agent 元數據"""

    version: str = Field("1.0.0", description="Agent 版本")
    description: Optional[str] = Field(None, description="Agent 描述")
    author: Optional[str] = Field(None, description="開發者/團隊")
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    capabilities: Dict[str, Any] = Field(default_factory=dict, description="能力描述")
    icon: Optional[str] = Field(None, description="圖標名稱（react-icons 圖標名稱，例如：FaRobot）")

    # 兼容舊代碼：添加別名屬性
    @property
    def purpose(self) -> Optional[str]:
        """用途（兼容舊代碼，使用 description）"""
        return self.description

    @property
    def category(self) -> Optional[str]:
        """類別（兼容舊代碼，從 tags 中提取或返回 None）"""
        # 可以從 tags 中提取類別，或返回 None
        return None


class AgentRegistryInfo(BaseModel):
    """Agent Registry 信息"""

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型（planning/execution/review）")
    name: str = Field(..., description="Agent 名稱")
    status: AgentStatus = Field(AgentStatus.REGISTERING, description="Agent 狀態")
    endpoints: AgentEndpoints = Field(..., description="Agent 端點配置")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: AgentMetadata = Field(default_factory=AgentMetadata, description="元數據")  # type: ignore[arg-type]  # default_factory 接受類型
    permissions: AgentPermissionConfig = Field(
        default_factory=AgentPermissionConfig, description="權限配置"
    )  # type: ignore[arg-type]  # default_factory 接受類型
    registered_at: datetime = Field(default_factory=datetime.now, description="註冊時間")
    last_heartbeat: Optional[datetime] = Field(None, description="最後心跳時間")
    load: int = Field(0, description="當前負載")

    # System Agent 標記（用於過濾前端顯示）
    is_system_agent: bool = Field(False, description="是否為 System Agent（系統內部 Agent，不會在前端顯示）")

    # 兼容舊代碼：添加額外屬性
    extra: Dict[str, Any] = Field(default_factory=dict, description="額外信息（兼容舊代碼）")

    @property
    def last_updated(self) -> datetime:
        """最後更新時間（兼容舊代碼，使用 last_heartbeat 或 registered_at）"""
        return self.last_heartbeat or self.registered_at


class AgentRegistrationRequest(BaseModel):
    """Agent 註冊請求

    用於註冊內部或外部 Agent 的請求模型。

    內部 Agent 註冊示例：
        request = AgentRegistrationRequest(
            agent_id="planning-agent-1",
            agent_type="planning",
            name="Planning Agent",
            endpoints=AgentEndpoints(
                http=None,
                mcp=None,
                protocol=AgentServiceProtocolType.HTTP,
                is_internal=True  # 標記為內部 Agent
            ),
            capabilities=["planning", "task_analysis"],
            permissions=AgentPermissionConfig()  # 內部 Agent 使用默認權限（完整權限）
        )

    外部 Agent 註冊示例：
        request = AgentRegistrationRequest(
            agent_id="partner-agent-1",
            agent_type="execution",
            name="Partner Execution Agent",
            endpoints=AgentEndpoints(
                http="https://partner-service.example.com",
                mcp=None,
                protocol=AgentServiceProtocolType.HTTP,
                is_internal=False  # 標記為外部 Agent
            ),
            capabilities=["execution", "custom_tools"],
            permissions=AgentPermissionConfig(
                allowed_memory_namespaces=["partner:memory"],
                allowed_tools=["tool1", "tool2"],
                allowed_llm_providers=["openai"],
                api_key="secret-api-key",
                ip_whitelist=["192.168.1.0/24"]
            )
        )
    """

    agent_id: str = Field(..., description="Agent ID")
    agent_type: str = Field(..., description="Agent 類型")
    name: str = Field(..., description="Agent 名稱")
    endpoints: AgentEndpoints = Field(..., description="Agent 端點配置（包含 is_internal 標誌）")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    metadata: Optional[AgentMetadata] = Field(None, description="元數據")
    permissions: Optional[AgentPermissionConfig] = Field(None, description="權限配置（包含資源訪問權限和認證配置）")
