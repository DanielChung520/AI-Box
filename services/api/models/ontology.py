# 代碼功能說明: Ontology 數據模型
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Ontology 數據模型定義"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from services.api.models.data_classification import (
    validate_classification,
    validate_sensitivity_labels,
)


class OntologyEntityClass(BaseModel):
    """Ontology 實體類別"""

    name: str = Field(description="實體名稱")
    description: Optional[str] = Field(default=None, description="實體描述")
    base_class: Optional[str] = Field(default=None, description="基礎類別")
    role: Optional[str] = Field(default=None, description="5W1H 角色")


class OntologyObjectProperty(BaseModel):
    """Ontology 物件屬性"""

    name: str = Field(description="屬性名稱")
    description: Optional[str] = Field(default=None, description="屬性描述")
    domain: List[str] = Field(description="Domain 類型列表")
    range: List[str] = Field(description="Range 類型列表")


class OntologyModel(BaseModel):
    """Ontology 數據模型"""

    id: Optional[str] = Field(default=None, description="Ontology ID（_key）")
    tenant_id: Optional[str] = Field(default=None, description="租戶 ID，null 表示全局共享")
    type: str = Field(description="Ontology 類型：base/domain/major")
    name: str = Field(description="Ontology 名稱")
    version: str = Field(description="版本號（語義化版本）")
    default_version: bool = Field(default=False, description="是否為默認版本")
    ontology_name: str = Field(description="完整 Ontology 名稱")
    description: Optional[str] = Field(default=None, description="描述")
    author: Optional[str] = Field(default=None, description="作者")
    last_modified: Optional[str] = Field(default=None, description="最後修改日期")
    inherits_from: List[str] = Field(default_factory=list, description="繼承的 Ontology 名稱列表")
    compatible_domains: List[str] = Field(
        default_factory=list, description="兼容的 domain（僅 major 類型）"
    )
    tags: List[str] = Field(default_factory=list, description="標籤列表")
    use_cases: List[str] = Field(default_factory=list, description="使用場景列表")
    entity_classes: List[OntologyEntityClass] = Field(
        default_factory=list, description="實體類別列表"
    )
    object_properties: List[OntologyObjectProperty] = Field(
        default_factory=list, description="物件屬性列表"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他元數據")
    is_active: bool = Field(default=True, description="是否啟用")
    # WBS-4.2.1: 數據分類與標記
    data_classification: Optional[str] = Field(
        default=None, description="數據分類級別（public/internal/confidential/restricted）"
    )
    sensitivity_labels: Optional[List[str]] = Field(
        default=None, description="敏感性標籤列表（可多選）"
    )
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    created_by: Optional[str] = Field(default=None, description="創建者")
    updated_by: Optional[str] = Field(default=None, description="更新者")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """驗證 type 字段"""
        if v not in ["base", "domain", "major"]:
            raise ValueError("type must be one of: base, domain, major")
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


class OntologyCreate(BaseModel):
    """Ontology 創建請求模型"""

    type: str
    name: str
    version: str
    default_version: bool = False
    ontology_name: str
    description: Optional[str] = None
    author: Optional[str] = None
    last_modified: Optional[str] = None
    inherits_from: List[str] = Field(default_factory=list)
    compatible_domains: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    use_cases: List[str] = Field(default_factory=list)
    entity_classes: List[Dict[str, Any]] = Field(default_factory=list)
    object_properties: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None
    # WBS-4.2.1: 數據分類與標記
    data_classification: Optional[str] = Field(
        default=None, description="數據分類級別（public/internal/confidential/restricted）"
    )
    sensitivity_labels: Optional[List[str]] = Field(
        default=None, description="敏感性標籤列表（可多選）"
    )


class OntologyUpdate(BaseModel):
    """Ontology 更新請求模型"""

    description: Optional[str] = None
    tags: Optional[List[str]] = None
    use_cases: Optional[List[str]] = None
    entity_classes: Optional[List[Dict[str, Any]]] = None
    object_properties: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    default_version: Optional[bool] = None
    # WBS-4.2.1: 數據分類與標記
    data_classification: Optional[str] = None
    sensitivity_labels: Optional[List[str]] = None
