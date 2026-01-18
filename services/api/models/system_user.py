# 代碼功能說明: SystemUser 數據模型
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:13 UTC+8

"""SystemUser 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SystemUserModel(BaseModel):
    """SystemUser 數據模型"""

    id: Optional[str] = Field(default=None, description="User ID（_key）")
    user_id: str = Field(description="用戶 ID（唯一）")
    username: str = Field(description="用戶名（唯一）")
    email: str = Field(description="郵箱地址")
    password_hash: Optional[str] = Field(default=None, description="密碼哈希（bcrypt）")
    roles: List[str] = Field(default_factory=list, description="角色列表")
    permissions: List[str] = Field(default_factory=list, description="權限列表")
    is_active: bool = Field(default=True, description="是否啟用")
    is_system_user: bool = Field(default=True, description="是否系統用戶")
    security_level: str = Field(default="highest", description="安全等級")
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: str) -> str:
        """驗證安全等級"""
        valid_levels = ["highest", "high", "medium", "low"]
        if v not in valid_levels:
            raise ValueError(f"security_level must be one of {valid_levels}")
        return v

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "example": {
                "id": "systemAdmin",
                "user_id": "systemAdmin",
                "username": "systemAdmin",
                "email": "system@ai-box.internal",
                "roles": ["system_admin"],
                "permissions": ["*"],
                "is_active": True,
                "is_system_user": True,
                "security_level": "highest",
                "metadata": {
                    "hidden_from_external": True,
                    "last_login_at": None,
                    "login_count": 0,
                },
            }
        }


class SystemUserCreate(BaseModel):
    """SystemUser 創建請求模型"""

    user_id: str = Field(description="用戶 ID（唯一）")
    username: str = Field(description="用戶名（唯一）")
    email: str = Field(description="郵箱地址")
    password: str = Field(description="密碼（明文，將被哈希）")
    roles: Optional[List[str]] = Field(default=None, description="角色列表")
    permissions: Optional[List[str]] = Field(default=None, description="權限列表")
    is_active: bool = Field(default=True, description="是否啟用")
    security_level: str = Field(default="highest", description="安全等級")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元數據")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """驗證密碼強度"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: str) -> str:
        """驗證安全等級"""
        valid_levels = ["highest", "high", "medium", "low"]
        if v not in valid_levels:
            raise ValueError(f"security_level must be one of {valid_levels}")
        return v


class SystemUserUpdate(BaseModel):
    """SystemUser 更新請求模型"""

    username: Optional[str] = Field(default=None, description="用戶名")
    email: Optional[str] = Field(default=None, description="郵箱地址")
    roles: Optional[List[str]] = Field(default=None, description="角色列表")
    permissions: Optional[List[str]] = Field(default=None, description="權限列表")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")
    security_level: Optional[str] = Field(default=None, description="安全等級")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元數據")

    @field_validator("security_level")
    @classmethod
    def validate_security_level(cls, v: Optional[str]) -> Optional[str]:
        """驗證安全等級"""
        if v is not None:
            valid_levels = ["highest", "high", "medium", "low"]
            if v not in valid_levels:
                raise ValueError(f"security_level must be one of {valid_levels}")
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
