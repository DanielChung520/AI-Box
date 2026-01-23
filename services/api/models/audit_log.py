# 代碼功能說明: 審計日誌數據模型
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""審計日誌數據模型定義。"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """審計操作類型枚舉（WBS-4: AI 治理與合規）"""

    # 文件操作
    FILE_UPLOAD = "file_upload"  # 文件上傳
    FILE_CREATE = "file_create"  # 文件創建
    FILE_UPDATE = "file_update"  # 文件更新
    FILE_ACCESS = "file_access"  # 文件訪問
    FILE_DELETE = "file_delete"  # 文件刪除
    DATA_PROCESS = "data_process"  # 數據處理

    # 任務操作
    TASK_CREATE = "task_create"  # 任務創建
    TASK_VIEW = "task_view"  # 任務訪問
    TASK_UPDATE = "task_update"  # 任務更新
    TASK_DELETE = "task_delete"  # 任務刪除

    # Ontology 操作（WBS-4.1.1）
    ONTOLOGY_CREATE = "ontology_create"  # Ontology 創建
    ONTOLOGY_READ = "ontology_read"  # Ontology 讀取
    ONTOLOGY_UPDATE = "ontology_update"  # Ontology 更新
    ONTOLOGY_DELETE = "ontology_delete"  # Ontology 刪除
    ONTOLOGY_MERGE = "ontology_merge"  # Ontology 合併

    # Config 操作（WBS-4.1.1）
    CONFIG_CREATE = "config_create"  # Config 創建
    CONFIG_READ = "config_read"  # Config 讀取
    CONFIG_UPDATE = "config_update"  # Config 更新
    CONFIG_DELETE = "config_delete"  # Config 刪除
    CONFIG_RESOLVE = "config_resolve"  # Config 解析

    # 其他操作
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
    USER_CREATE = "user_create"  # 用戶創建
    USER_UPDATE = "user_update"  # 用戶更新
    USER_DELETE = "user_delete"  # 用戶刪除
    SYSTEM_ACTION = "system_action"  # 系統操作（服務檢查等）


class AuditLog(BaseModel):
    """審計日誌模型"""

    user_id: str = Field(..., description="用戶ID")
    action: AuditAction = Field(..., description="操作類型")
    resource_type: str = Field(..., description="資源類型（file, task, etc.）")
    resource_id: Optional[str] = Field(None, description="資源ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="操作時間")
    ip_address: str = Field(..., description="IP 地址")
    user_agent: str = Field(..., description="User Agent")
    details: Dict[str, Any] = Field(default_factory=dict, description="額外詳情（JSON）")

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
