# 代碼功能說明: 變更提案數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""變更提案數據模型定義。"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProposalStatus(str, Enum):
    """提案狀態枚舉"""

    PENDING = "PENDING"  # 待審批
    APPROVED = "APPROVED"  # 已批准
    REJECTED = "REJECTED"  # 已拒絕


class ChangeProposal(BaseModel):
    """變更提案模型"""

    proposal_id: str = Field(..., description="提案 ID")
    proposal_type: str = Field(..., description="提案類型（如 config_update, ontology_update）")
    resource_id: Optional[str] = Field(None, description="資源 ID（可選）")
    proposed_by: str = Field(..., description="提案者（用戶 ID）")
    status: ProposalStatus = Field(default=ProposalStatus.PENDING, description="提案狀態")
    proposal_data: Dict[str, Any] = Field(default_factory=dict, description="提案數據")
    approval_required: bool = Field(default=True, description="是否需要審批")
    approved_by: Optional[str] = Field(None, description="審批者（用戶 ID）")
    approved_at: Optional[datetime] = Field(None, description="審批時間")
    rejected_by: Optional[str] = Field(None, description="拒絕者（用戶 ID）")
    rejected_at: Optional[datetime] = Field(None, description="拒絕時間")
    rejection_reason: Optional[str] = Field(None, description="拒絕原因")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="更新時間")

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class ChangeProposalCreate(BaseModel):
    """創建變更提案的請求模型"""

    proposal_type: str
    resource_id: Optional[str] = None
    proposed_by: str
    proposal_data: Dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = True

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
