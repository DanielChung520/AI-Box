# 代碼功能說明: Agent 認證服務數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent 認證服務數據模型定義"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AuthenticationStatus(str, Enum):
    """認證狀態"""

    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"


class AuthenticationResult(BaseModel):
    """認證結果"""

    status: AuthenticationStatus = Field(..., description="認證狀態")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    message: Optional[str] = Field(None, description="認證消息")
    error: Optional[str] = Field(None, description="錯誤信息")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


class InternalAuthConfig(BaseModel):
    """內部 Agent 認證配置"""

    service_identity: Optional[str] = Field(
        None, description="服務標識（可選，用於額外驗證）"
    )
    require_identity: bool = Field(False, description="是否要求服務標識")


class ExternalAuthConfig(BaseModel):
    """外部 Agent 認證配置"""

    api_key: Optional[str] = Field(None, description="API Key")
    server_certificate: Optional[str] = Field(
        None, description="服務器證書（PEM 格式）"
    )
    ip_whitelist: List[str] = Field(default_factory=list, description="IP 白名單列表")
    server_fingerprint: Optional[str] = Field(None, description="服務器指紋")
    require_mtls: bool = Field(False, description="是否要求 mTLS")
    require_signature: bool = Field(False, description="是否要求請求簽名")
    require_ip_check: bool = Field(False, description="是否要求 IP 白名單檢查")
