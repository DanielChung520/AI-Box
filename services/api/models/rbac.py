# 代碼功能說明: RBAC 數據模型
# 創建日期: 2025-12-06 15:20 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:20 (UTC+8)

"""RBAC 數據模型 - 定義角色、權限和用戶角色關聯"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class PermissionModel(BaseModel):
    """權限模型"""

    permission_id: str = Field(..., description="權限ID")
    name: str = Field(..., description="權限名稱")
    description: Optional[str] = Field(None, description="權限描述")
    resource_type: Optional[str] = Field(None, description="資源類型（如 file, task）")
    action: Optional[str] = Field(None, description="操作類型（如 read, write, delete）")
    created_at: Optional[datetime] = Field(None, description="創建時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    class Config:
        from_attributes = True


class RoleModel(BaseModel):
    """角色模型"""

    role_id: str = Field(..., description="角色ID")
    name: str = Field(..., description="角色名稱")
    description: Optional[str] = Field(None, description="角色描述")
    permissions: List[str] = Field(default_factory=list, description="權限ID列表")
    is_system: bool = Field(False, description="是否為系統角色")
    created_at: Optional[datetime] = Field(None, description="創建時間")
    updated_at: Optional[datetime] = Field(None, description="更新時間")

    class Config:
        from_attributes = True


class UserRoleModel(BaseModel):
    """用戶角色關聯模型"""

    user_id: str = Field(..., description="用戶ID")
    role_id: str = Field(..., description="角色ID")
    assigned_at: Optional[datetime] = Field(None, description="分配時間")
    assigned_by: Optional[str] = Field(None, description="分配者用戶ID")
    expires_at: Optional[datetime] = Field(None, description="過期時間（可選）")

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    """創建角色請求模型"""

    name: str = Field(..., description="角色名稱")
    description: Optional[str] = Field(None, description="角色描述")
    permissions: List[str] = Field(default_factory=list, description="權限ID列表")
    is_system: bool = Field(False, description="是否為系統角色")


class RoleUpdate(BaseModel):
    """更新角色請求模型"""

    name: Optional[str] = Field(None, description="角色名稱")
    description: Optional[str] = Field(None, description="角色描述")
    permissions: Optional[List[str]] = Field(None, description="權限ID列表")


class UserRoleAssign(BaseModel):
    """分配用戶角色請求模型"""

    user_id: str = Field(..., description="用戶ID")
    role_id: str = Field(..., description="角色ID")
    expires_at: Optional[datetime] = Field(None, description="過期時間（可選）")


class UserRoleRevoke(BaseModel):
    """撤銷用戶角色請求模型"""

    user_id: str = Field(..., description="用戶ID")
    role_id: str = Field(..., description="角色ID")
