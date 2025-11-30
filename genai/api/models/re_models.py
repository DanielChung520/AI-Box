# 代碼功能說明: RE 關係抽取數據模型
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RE 關係抽取數據模型 - 定義 Pydantic Model"""

from typing import List, Optional
from pydantic import BaseModel, Field

from genai.api.models.ner_models import Entity


class RelationEntity(BaseModel):
    """關係中的實體模型"""

    text: str = Field(..., description="實體文本")
    label: str = Field(..., description="實體類型")


class Relation(BaseModel):
    """關係模型"""

    subject: RelationEntity = Field(..., description="主體實體")
    relation: str = Field(
        ...,
        description="關係類型（LOCATED_IN, WORKS_FOR, PART_OF, RELATED_TO, OCCURS_AT 等）",
    )
    object: RelationEntity = Field(..., description="客體實體")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0-1）")
    context: str = Field(..., description="關係出現的上下文")


class RERequest(BaseModel):
    """RE 請求模型"""

    text: str = Field(..., description="待抽取關係的文本")
    entities: Optional[List[Entity]] = Field(
        None, description="預先識別的實體列表（可選，如果不提供則自動識別）"
    )
    model_type: Optional[str] = Field(
        None,
        description="指定使用的模型類型（transformers/ollama），不指定則使用配置默認值",
    )


class REBatchRequest(BaseModel):
    """RE 批量請求模型"""

    texts: List[str] = Field(..., description="待抽取關係的文本列表")
    model_type: Optional[str] = Field(
        None,
        description="指定使用的模型類型（transformers/ollama），不指定則使用配置默認值",
    )


class REResponse(BaseModel):
    """RE 響應模型"""

    relations: List[Relation] = Field(default_factory=list, description="抽取出的關係列表")
    text: str = Field(..., description="原始文本")
    model_used: str = Field(..., description="實際使用的模型類型")


class REBatchResponse(BaseModel):
    """RE 批量響應模型"""

    results: List[REResponse] = Field(default_factory=list, description="每個文本的關係抽取結果")
    total: int = Field(..., description="總文本數")
    processed: int = Field(..., description="成功處理的文本數")
