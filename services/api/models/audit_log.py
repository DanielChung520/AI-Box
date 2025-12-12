# 代碼功能說明: 審計日誌數據模型
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""審計日誌數據模型定義。"""

from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """審計操作類型枚舉"""

    FILE_UPLOAD = "file_upload"  # 文件上傳
    FILE_CREATE = "file_create"  # 文件創建
    FILE_UPDATE = "file_update"  # 文件更新
    FILE_ACCESS = "file_access"  # 文件訪問
    FILE_DELETE = "file_delete"  # 文件刪除
    DATA_PROCESS = "data_process"  # 數據處理
    MODEL_CALL = "model_call"  # 模型調用
    CONSENT_GRANTED = "consent_granted"  # 同意授予
    CONSENT_REVOKED = "consent_revoked"  # 同意撤銷
    LOGIN = "login"  # 登錄
    LOGOUT = "logout"  # 登出
    TOKEN_REFRESH = "token_refresh"  # Token 刷新
    ROLE_CREATE = "role_create"  # 角色創建
    ROLE_UPDATE = "role_update"  # 角色更新
    ROLE_DELETE = "role_delete"  # 角色刪除
    USER_ROLE_ASSIGN = "user_role_assign"  # 用戶角色分配
    USER_ROLE_REVOKE = "user_role_revoke"  # 用戶角色撤銷


class AuditLog(BaseModel):
    """審計日誌模型"""

    user_id: str = Field(..., description="用戶ID")
    action: AuditAction = Field(..., description="操作類型")
    resource_type: str = Field(..., description="資源類型（file, task, etc.）")
    resource_id: Optional[str] = Field(None, description="資源ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="操作時間")
    ip_address: str = Field(..., description="IP 地址")
    user_agent: str = Field(..., description="User Agent")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="額外詳情（JSON）"
    )

    class Config:
        use_enum_values = True


class AuditLogCreate(BaseModel):
    """創建審計日誌的請求模型"""

    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: str
    user_agent: str
    details: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class AuditLogResponse(BaseModel):
    """審計日誌響應模型"""

    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: Optional[str] = None
    timestamp: datetime
    ip_address: str
    user_agent: str
    details: Dict[str, Any]

    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
