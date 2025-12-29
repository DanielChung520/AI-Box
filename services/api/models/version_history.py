# 代碼功能說明: 版本歷史數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""版本歷史數據模型定義。"""

from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class VersionHistory(BaseModel):
    """版本歷史記錄模型"""

    resource_type: str = Field(..., description="資源類型（如 ontologies, configs 等）")
    resource_id: str = Field(..., description="資源 ID")
    version: int = Field(..., description="版本號")
    change_type: str = Field(..., description="變更類型（create, update, delete）")
    changed_by: str = Field(..., description="變更者（用戶 ID）")
    change_summary: str = Field(..., description="變更摘要")
    previous_version: Dict[str, Any] = Field(default_factory=dict, description="前一版本的數據")
    current_version: Dict[str, Any] = Field(default_factory=dict, description="當前版本的數據")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="創建時間")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class VersionHistoryCreate(BaseModel):
    """創建版本歷史的請求模型"""

    resource_type: str
    resource_id: str
    change_type: str
    changed_by: str
    change_summary: str
    previous_version: Dict[str, Any] = Field(default_factory=dict)
    current_version: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
