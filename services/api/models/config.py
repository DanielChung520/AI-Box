# 代碼功能說明: Config 數據模型
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Config 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from services.api.models.data_classification import (
    validate_classification,
    validate_sensitivity_labels,
)


class ConfigModel(BaseModel):
    """Config 數據模型（通用）"""

    id: Optional[str] = Field(default=None, description="Config ID（_key）")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID，null 表示系統層")
    user_id: Optional[str] = Field(default=None, description="用戶 ID（僅 user_configs）")
    scope: str = Field(description="配置範圍，如 genai.policy, genai.model_registry")
    sub_scope: Optional[str] = Field(default=None, description="子範圍（可選）")
    category: Optional[str] = Field(
        default=None,
        description="配置分類：basic/feature_flag/performance/security/business",
    )
    is_active: bool = Field(default=True, description="是否啟用")
    config_data: Dict[str, Any] = Field(description="配置數據（JSON 對象）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
    # WBS-4.2.1: 數據分類與標記
    data_classification: Optional[str] = Field(
        default=None, description="數據分類級別（public/internal/confidential/restricted）"
    )
    sensitivity_labels: Optional[List[str]] = Field(default=None, description="敏感性標籤列表（可多選）")
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    created_by: Optional[str] = Field(default=None, description="創建者")
    updated_by: Optional[str] = Field(default=None, description="更新者")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """驗證配置分類"""
        if v is None:
            return None
        valid_categories = [
            "basic",
            "feature_flag",
            "performance",
            "security",
            "business",
        ]
        if v not in valid_categories:
            raise ValueError(f"category must be one of {valid_categories}, got {v}")
        return v

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


class ConfigCreate(BaseModel):
    """Config 創建請求模型"""

    scope: str
    sub_scope: Optional[str] = None
    category: Optional[str] = Field(
        default=None,
        description="配置分類：basic/feature_flag/performance/security/business",
    )
    config_data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    # WBS-4.2.1: 數據分類與標記
    data_classification: Optional[str] = Field(
        default=None, description="數據分類級別（public/internal/confidential/restricted）"
    )
    sensitivity_labels: Optional[List[str]] = Field(default=None, description="敏感性標籤列表（可多選）")


class ConfigUpdate(BaseModel):
    """Config 更新請求模型"""

    config_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    category: Optional[str] = Field(
        default=None,
        description="配置分類：basic/feature_flag/performance/security/business",
    )
    is_active: Optional[bool] = None
    # WBS-4.2.1: 數據分類與標記
    data_classification: Optional[str] = None
    sensitivity_labels: Optional[List[str]] = None


class EffectiveConfig(BaseModel):
    """有效配置（合併後的配置）"""

    scope: str
    tenant_id: Optional[str] = None
    user_id: Optional[str] = None
    config: Dict[str, Any] = Field(description="最終有效配置")
    merged_from: Dict[str, bool] = Field(description="合併來源標記：system/tenant/user")
