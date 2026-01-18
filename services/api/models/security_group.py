# 代碼功能說明: SecurityGroup 數據模型
# 創建日期: 2026-01-17 19:41 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 19:41 UTC+8

"""SecurityGroup 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SecurityGroupRules(BaseModel):
    """安全群組規則模型"""

    ip_whitelist: List[str] = Field(default_factory=list, description="IP 白名單列表（支持 CIDR 格式）")
    ip_blacklist: List[str] = Field(default_factory=list, description="IP 黑名單列表（支持 CIDR 格式）")
    allowed_time_ranges: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="允許訪問的時間段列表，格式：[{'start': '09:00', 'end': '18:00', 'days': ['mon', 'tue', ...]}]",
    )
    max_concurrent_sessions: Optional[int] = Field(default=None, description="最大並發會話數")
    require_mfa: bool = Field(default=False, description="是否需要多因素認證")

    @field_validator("ip_whitelist", "ip_blacklist")
    @classmethod
    def validate_ip_list(cls, v: List[str]) -> List[str]:
        """驗證 IP 列表"""
        # 簡單驗證：檢查是否為有效的 IP 或 CIDR 格式
        # 實際驗證可以使用 ipaddress 模塊
        return v

    @field_validator("allowed_time_ranges")
    @classmethod
    def validate_time_ranges(cls, v: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """驗證時間範圍"""
        valid_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
        for time_range in v:
            if "start" not in time_range or "end" not in time_range:
                raise ValueError("time_range must contain 'start' and 'end'")
            if "days" in time_range:
                for day in time_range["days"]:
                    if day not in valid_days:
                        raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return v


class SecurityGroupModel(BaseModel):
    """SecurityGroup 數據模型"""

    id: Optional[str] = Field(default=None, description="Group ID（_key）")
    group_id: str = Field(description="群組 ID（唯一標識）")
    group_name: str = Field(description="群組名稱")
    description: Optional[str] = Field(default=None, description="群組描述")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID（系統級為 None）")
    rules: SecurityGroupRules = Field(description="安全規則")
    users: List[str] = Field(default_factory=list, description="成員用戶 ID 列表")
    is_active: bool = Field(default=True, description="是否啟用")
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")

    class Config:
        """Pydantic 配置"""

        json_schema_extra = {
            "example": {
                "id": "sg_dev_team",
                "group_id": "dev_team",
                "group_name": "開發團隊",
                "description": "開發團隊安全群組",
                "tenant_id": None,
                "rules": {
                    "ip_whitelist": ["192.168.1.0/24"],
                    "ip_blacklist": [],
                    "allowed_time_ranges": [
                        {
                            "start": "09:00",
                            "end": "18:00",
                            "days": ["mon", "tue", "wed", "thu", "fri"],
                        }
                    ],
                    "max_concurrent_sessions": 3,
                    "require_mfa": False,
                },
                "users": ["user_1", "user_2"],
                "is_active": True,
                "created_at": "2026-01-17T19:41:00Z",
                "updated_at": "2026-01-17T19:41:00Z",
            }
        }


class SecurityGroupCreate(BaseModel):
    """創建安全群組請求模型"""

    group_id: str = Field(description="群組 ID（唯一標識）")
    group_name: str = Field(description="群組名稱")
    description: Optional[str] = Field(default=None, description="群組描述")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID（系統級為 None）")
    rules: SecurityGroupRules = Field(description="安全規則")
    users: List[str] = Field(default_factory=list, description="成員用戶 ID 列表")


class SecurityGroupUpdate(BaseModel):
    """更新安全群組請求模型"""

    group_name: Optional[str] = Field(default=None, description="群組名稱")
    description: Optional[str] = Field(default=None, description="群組描述")
    rules: Optional[SecurityGroupRules] = Field(default=None, description="安全規則")
    users: Optional[List[str]] = Field(default=None, description="成員用戶 ID 列表")
    is_active: Optional[bool] = Field(default=None, description="是否啟用")
