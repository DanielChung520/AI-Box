# 代碼功能說明: 語義轉譯數據模型
# 創建日期: 2026-02-05
# 創建人: Daniel Chung

"""語義轉譯數據模型"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ConceptMapping(BaseModel):
    """詞彙轉譯結果"""

    canonical_id: str = Field(..., description="標準概念 ID")
    source_terms: List[str] = Field(default_factory=list, description="原始用詞")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")


class SchemaBinding(BaseModel):
    """Schema 綁定"""

    primary_table: Optional[str] = Field(default=None, description="主要資料表")
    tables: List[str] = Field(default_factory=list, description="可能使用的資料表")
    columns: List[str] = Field(default_factory=list, description="可能使用的欄位")


class Constraints(BaseModel):
    """查詢約束條件"""

    material_id: Optional[str] = Field(default=None, description="料號")
    inventory_location: Optional[str] = Field(default=None, description="倉庫")
    material_category: Optional[str] = Field(default=None, description="物料類別")
    time_range: Optional[Dict[str, Any]] = Field(default=None, description="時間範圍")
    transaction_type: Optional[str] = Field(default=None, description="交易類型")
    quantity: Optional[int] = Field(default=None, description="數量")
    supplier: Optional[str] = Field(default=None, description="供應商")
    customer: Optional[str] = Field(default=None, description="客戶")


class Validation(BaseModel):
    """驗證結果"""

    requires_confirmation: bool = Field(default=False, description="是否需要確認")
    missing_fields: List[str] = Field(default_factory=list, description="缺少的欄位")
    notes: str = Field(default="", description="備註")


class SemanticTranslationResult(BaseModel):
    """語義轉譯結果"""

    intent: str = Field(..., description="意圖類型")
    concepts: List[ConceptMapping] = Field(default_factory=list, description="概念映射")
    schema_binding: SchemaBinding = Field(
        default_factory=lambda: SchemaBinding(), description="Schema 綁定"
    )
    constraints: Constraints = Field(default_factory=lambda: Constraints(), description="約束條件")
    validation: Validation = Field(default_factory=lambda: Validation(), description="驗證結果")
    raw_text: str = Field(..., description="原始輸入")
