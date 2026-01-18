# 代碼功能說明: Agent 註冊申請數據模型
# 創建日期: 2026-01-17 18:27 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 18:27 UTC+8

"""Agent 註冊申請數據模型定義"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentRegistrationStatus(str, Enum):
    """Agent 註冊申請狀態枚舉"""

    PENDING = "pending"  # 待審核
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒絕
    REVOKED = "revoked"  # 已撤銷


class ApplicantInfo(BaseModel):
    """申請者信息"""

    name: str = Field(..., description="申請者姓名")
    email: str = Field(..., description="申請者郵箱")
    company: Optional[str] = Field(default=None, description="公司名稱")
    contact_phone: Optional[str] = Field(default=None, description="聯繫電話")


class AgentConfigRequest(BaseModel):
    """Agent 技術配置請求"""

    agent_type: str = Field(..., description="Agent 類型（execution/planning/review）")
    protocol: str = Field(..., description="通信協議（http/mcp）")
    endpoint_url: str = Field(..., description="Agent 端點 URL")
    capabilities: List[str] = Field(default_factory=list, description="能力列表")
    input_schema: Optional[Dict[str, Any]] = Field(
        default=None, description="輸入 Schema（JSON Schema）"
    )


class RequestedPermissions(BaseModel):
    """請求的權限配置"""

    tools: List[str] = Field(default_factory=list, description="工具列表（支持通配符，如 finance_*）")
    rate_limits: Dict[str, int] = Field(default_factory=dict, description="速率限制配置")
    access_level: str = Field(default="tenant", description="訪問級別（system/tenant/user）")


class SecretInfo(BaseModel):
    """Secret 信息"""

    secret_id: Optional[str] = Field(default=None, description="Secret ID")
    secret_key_hash: Optional[str] = Field(default=None, description="Secret Key 哈希（bcrypt）")
    issued_at: Optional[datetime] = Field(default=None, description="簽發時間")
    expires_at: Optional[datetime] = Field(default=None, description="過期時間")


class ReviewInfo(BaseModel):
    """審查信息"""

    reviewed_by: Optional[str] = Field(default=None, description="審查人 user_id")
    reviewed_at: Optional[datetime] = Field(default=None, description="審查時間")
    review_notes: Optional[str] = Field(default=None, description="審查意見")
    rejection_reason: Optional[str] = Field(default=None, description="拒絕原因")


class AgentRegistrationRequestModel(BaseModel):
    """Agent 註冊申請模型"""

    id: Optional[str] = Field(default=None, description="申請記錄 ID（ArangoDB _key）")
    request_id: str = Field(..., description="申請 ID")
    agent_id: str = Field(..., description="Agent ID（由申請者提供）")
    agent_name: str = Field(..., description="Agent 名稱")
    agent_description: Optional[str] = Field(default=None, description="Agent 描述")
    applicant_info: ApplicantInfo = Field(..., description="申請者信息")
    agent_config: AgentConfigRequest = Field(..., description="Agent 技術配置")
    requested_permissions: RequestedPermissions = Field(..., description="請求的權限")
    status: AgentRegistrationStatus = Field(
        default=AgentRegistrationStatus.PENDING, description="申請狀態"
    )
    secret_info: SecretInfo = Field(default_factory=SecretInfo, description="Secret 信息")
    review_info: ReviewInfo = Field(default_factory=ReviewInfo, description="審查信息")
    tenant_id: Optional[str] = Field(default=None, description="所屬租戶 ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據（IP、User-Agent 等）")

    class Config:
        populate_by_name = True
        use_enum_values = True


class AgentRegistrationRequestCreate(BaseModel):
    """創建 Agent 註冊申請請求模型"""

    agent_id: str = Field(..., description="Agent ID（由申請者提供）")
    agent_name: str = Field(..., description="Agent 名稱")
    agent_description: Optional[str] = Field(default=None, description="Agent 描述")
    applicant_info: ApplicantInfo = Field(..., description="申請者信息")
    agent_config: AgentConfigRequest = Field(..., description="Agent 技術配置")
    requested_permissions: RequestedPermissions = Field(..., description="請求的權限")
    tenant_id: Optional[str] = Field(default=None, description="所屬租戶 ID")


class AgentRegistrationRequestUpdate(BaseModel):
    """更新 Agent 註冊申請請求模型"""

    agent_name: Optional[str] = Field(default=None, description="Agent 名稱")
    agent_description: Optional[str] = Field(default=None, description="Agent 描述")
    applicant_info: Optional[ApplicantInfo] = Field(default=None, description="申請者信息")
    agent_config: Optional[AgentConfigRequest] = Field(default=None, description="Agent 技術配置")
    requested_permissions: Optional[RequestedPermissions] = Field(default=None, description="請求的權限")


class ApproveRequest(BaseModel):
    """批准申請請求模型"""

    review_notes: Optional[str] = Field(default=None, description="審查意見")


class RejectRequest(BaseModel):
    """拒絕申請請求模型"""

    rejection_reason: str = Field(..., description="拒絕原因")
    review_notes: Optional[str] = Field(default=None, description="審查意見")


class RevokeRequest(BaseModel):
    """撤銷申請請求模型"""

    revoke_reason: str = Field(..., description="撤銷原因")


class ApproveResponse(BaseModel):
    """批准申請響應模型（包含 Secret）"""

    request_id: str
    agent_id: str
    secret_id: str
    secret_key: str  # ⚠️ 僅在批准時一次性返回，之後不再提供
    message: str = Field(default="請立即複製 Secret Key，此密鑰僅顯示一次")


class AgentRegistrationRequestResponse(BaseModel):
    """Agent 註冊申請響應模型"""

    id: str
    request_id: str
    agent_id: str
    agent_name: str
    agent_description: Optional[str]
    applicant_info: ApplicantInfo
    agent_config: AgentConfigRequest
    requested_permissions: RequestedPermissions
    status: AgentRegistrationStatus
    secret_info: SecretInfo  # 不包含 secret_key，僅包含 secret_id
    review_info: ReviewInfo
    tenant_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any]
