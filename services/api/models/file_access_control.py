# 代碼功能說明: 文件訪問控制模型定義
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件訪問控制模型定義

定義文件訪問級別和訪問控制配置的模型。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from services.api.models.data_classification import (
    DataClassification,
    validate_classification,
    validate_sensitivity_labels,
)


class FileAccessLevel(str, Enum):
    """文件訪問級別枚舉"""

    PUBLIC = "public"  # 全局公開：全公司可見
    ORGANIZATION = "organization"  # 組織級：授權組織部分可見
    SECURITY_GROUP = "security_group"  # 安全組級：特定安全組授權
    PRIVATE = "private"  # 私有：只有授權用戶可見（默認）

    @classmethod
    def get_all_values(cls) -> List[str]:
        """獲取所有訪問級別的值"""
        return [item.value for item in cls]

    @classmethod
    def validate(cls, value: str) -> str:
        """驗證訪問級別是否有效"""
        valid_values = cls.get_all_values()
        if value not in valid_values:
            raise ValueError(
                f"Invalid access level: {value}. " f"Must be one of: {', '.join(valid_values)}"
            )
        return value


class FileAccessControl(BaseModel):
    """文件訪問控制模型"""

    # 訪問級別（優先級從高到低）
    access_level: str = Field(
        ...,
        description="訪問級別: PUBLIC | ORGANIZATION | SECURITY_GROUP | PRIVATE",
    )

    # 組織級授權（access_level = ORGANIZATION）
    authorized_organizations: Optional[List[str]] = Field(
        None,
        description="授權組織ID列表（僅當 access_level=ORGANIZATION 時使用）",
    )

    # 安全組級授權（access_level = SECURITY_GROUP）
    authorized_security_groups: Optional[List[str]] = Field(
        None,
        description="授權安全組ID列表（僅當 access_level=SECURITY_GROUP 時使用）",
    )

    # 用戶級授權（access_level = PRIVATE）
    authorized_users: Optional[List[str]] = Field(
        None,
        description="授權用戶ID列表（僅當 access_level=PRIVATE 時使用，默認包含 owner）",
    )

    # 數據分類（AI治理要求）
    data_classification: Optional[str] = Field(
        default=DataClassification.INTERNAL.value,
        description="數據分類級別: public | internal | confidential | restricted",
    )

    # 敏感性標籤（AI治理要求）
    sensitivity_labels: Optional[List[str]] = Field(
        default_factory=list,
        description="敏感性標籤列表: PII, PHI, FINANCIAL, IP, CUSTOMER, PROPRIETARY",
    )

    # 所有者信息
    owner_id: str = Field(..., description="文件所有者用戶ID")
    owner_tenant_id: Optional[str] = Field(None, description="文件所有者租戶ID")

    # 審計字段
    access_log_enabled: bool = Field(
        default=True,
        description="是否啟用訪問日誌（AI治理要求）",
    )

    # 過期時間（可選）
    access_expires_at: Optional[datetime] = Field(
        None,
        description="訪問權限過期時間（可選，用於臨時授權）",
    )

    @field_validator("access_level")
    @classmethod
    def validate_access_level(cls, v: str) -> str:
        """驗證訪問級別"""
        return FileAccessLevel.validate(v)

    @field_validator("data_classification")
    @classmethod
    def validate_data_classification(cls, v: Optional[str]) -> Optional[str]:
        """驗證數據分類級別"""
        return validate_classification(v)

    @field_validator("sensitivity_labels")
    @classmethod
    def validate_sensitivity_labels(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """驗證敏感性標籤列表"""
        return validate_sensitivity_labels(v)

    @field_validator("authorized_organizations", "authorized_security_groups", "authorized_users")
    @classmethod
    def validate_authorized_lists(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """驗證授權列表（確保不為空列表）"""
        if v is not None and len(v) == 0:
            return None
        return v

    def model_post_init(self, __context) -> None:
        """模型初始化後處理"""
        # 確保 PRIVATE 級別時，authorized_users 至少包含 owner_id
        if self.access_level == FileAccessLevel.PRIVATE.value:
            if self.authorized_users is None:
                self.authorized_users = [self.owner_id]
            elif self.owner_id not in self.authorized_users:
                self.authorized_users.append(self.owner_id)

    class Config:
        """Pydantic 配置"""

        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None,
        }
