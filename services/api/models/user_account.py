# 代碼功能說明: UserAccount 數據模型
# 創建日期: 2026-01-17 17:18 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:18 UTC+8

"""UserAccount 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserAccountModel(BaseModel):
    """UserAccount 數據模型"""

    id: Optional[str] = Field(default=None, description="User ID（_key）")
    user_id: str = Field(description="用戶 ID（唯一）")
    username: str = Field(description="用戶名（唯一）")
    email: EmailStr = Field(description="郵箱地址")
    password_hash: Optional[str] = Field(default=None, description="密碼哈希（bcrypt）")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID")
    roles: List[str] = Field(default_factory=list, description="角色列表")
    permissions: List[str] = Field(default_factory=list, description="權限列表")
    is_active: bool = Field(default=True, description="是否啟用")
    is_system_user: bool = Field(default=False, description="是否系統用戶")
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    last_login_at: Optional[datetime] = Field(default=None, description="最後登錄時間")
    login_count: int = Field(default=0, description="登錄次數")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "example": {
                "id": "user_123",
                "user_id": "user_123",
                "username": "john_doe",
                "email": "john@example.com",
                "roles": ["user"],
                "permissions": ["file:upload", "file:read:own"],
                "is_active": True,
                "is_system_user": False,
                "last_login_at": None,
                "login_count": 0,
            }
        }


class UserAccountCreate(BaseModel):
    """UserAccount 創建請求模型"""

    user_id: Optional[str] = Field(default=None, description="用戶 ID（可選，自動生成）")
    username: str = Field(description="用戶名（唯一）")
    email: EmailStr = Field(description="郵箱地址")
    password: str = Field(description="密碼（明文，將被哈希）")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID")
    roles: Optional[List[str]] = Field(default=None, description="角色列表")
    permissions: Optional[List[str]] = Field(default=None, description="權限列表")
    is_active: bool = Field(default=True, description="是否啟用")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元數據")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """驗證密碼強度"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """驗證用戶名格式"""
        if not v or len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        return v


class UserAccountUpdate(BaseModel):
    """UserAccount 更新請求模型"""

    username: Optional[str] = Field(default=None, description="用戶名")
    email: Optional[EmailStr] = Field(default=None, description="郵箱地址")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID")
    roles: Optional[List[str]] = Field(default=None, description="角色列表")
    permissions: Optional[List[str]] = Field(default=None, description="權限列表")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元數據")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """驗證用戶名格式"""
        if v is not None:
            if len(v) < 3:
                raise ValueError("Username must be at least 3 characters long")
            if not v.replace("_", "").replace("-", "").isalnum():
                raise ValueError(
                    "Username can only contain letters, numbers, underscores, and hyphens"
                )
        return v


class PasswordResetRequest(BaseModel):
    """密碼重置請求模型"""

    new_password: str = Field(description="新密碼（明文，將被哈希）")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """驗證密碼強度"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserRoleAssignment(BaseModel):
    """用戶角色分配請求模型"""

    role_id: str = Field(description="角色 ID")


class UserRoleRevoke(BaseModel):
    """用戶角色撤銷請求模型"""

    role_id: str = Field(description="角色 ID")
