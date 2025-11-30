# 代碼功能說明: RT 關係類型分類數據模型
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RT 關係類型分類數據模型 - 定義 Pydantic Model"""

from typing import List, Optional
from pydantic import BaseModel, Field


class RelationType(BaseModel):
    """關係類型模型"""

    type: str = Field(..., description="關係類型名稱")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0-1）")


class RTRequest(BaseModel):
    """RT 請求模型"""

    relation_text: str = Field(..., description="關係文本（例如：'工作於'、'位於' 等）")
    subject_text: Optional[str] = Field(None, description="主體實體文本（可選，用於上下文）")
    object_text: Optional[str] = Field(None, description="客體實體文本（可選，用於上下文）")
    model_type: Optional[str] = Field(
        None,
        description="指定使用的模型類型（ollama/transformers），不指定則使用配置默認值",
    )


class RTBatchRequest(BaseModel):
    """RT 批量請求模型"""

    relations: List[RTRequest] = Field(..., description="關係文本列表")
    model_type: Optional[str] = Field(
        None,
        description="指定使用的模型類型（ollama/transformers），不指定則使用配置默認值",
    )


class RTResponse(BaseModel):
    """RT 響應模型"""

    relation_text: str = Field(..., description="原始關係文本")
    relation_types: List[RelationType] = Field(
        default_factory=list, description="識別出的關係類型列表（多標籤）"
    )
    primary_type: Optional[str] = Field(None, description="主要關係類型（置信度最高的）")
    model_used: str = Field(..., description="實際使用的模型類型")


class RTBatchResponse(BaseModel):
    """RT 批量響應模型"""

    results: List[RTResponse] = Field(default_factory=list, description="每個關係的分類結果")
    total: int = Field(..., description="總關係數")
    processed: int = Field(..., description="成功處理的關係數")
