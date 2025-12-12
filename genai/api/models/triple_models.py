# 代碼功能說明: 三元組提取數據模型
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""三元組提取數據模型 - 定義 Pydantic Model"""

from typing import List, Optional
from pydantic import BaseModel, Field

from genai.api.models.ner_models import Entity


class TripleEntity(BaseModel):
    """三元組中的實體模型"""

    text: str = Field(..., description="實體文本")
    type: str = Field(..., description="實體類型")
    start: int = Field(..., description="實體在文本中的起始位置")
    end: int = Field(..., description="實體在文本中的結束位置")


class TripleRelation(BaseModel):
    """三元組中的關係模型"""

    type: str = Field(..., description="關係類型")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0-1）")


class Triple(BaseModel):
    """三元組模型"""

    subject: TripleEntity = Field(..., description="主體實體")
    relation: TripleRelation = Field(..., description="關係")
    object: TripleEntity = Field(..., description="客體實體")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="三元組整體置信度（綜合 NER、RE、RT 置信度）"
    )
    source_text: str = Field(..., description="原始文本")
    context: str = Field(..., description="上下文")


class TripleExtractionRequest(BaseModel):
    """三元組提取請求模型"""

    text: str = Field(..., description="待提取三元組的文本")
    enable_ner: bool = Field(
        True, description="是否啟用實體識別（如果為 False，則需要提供 entities）"
    )
    entities: Optional[List[Entity]] = Field(
        None, description="預先識別的實體列表（可選）"
    )


class TripleBatchRequest(BaseModel):
    """三元組批量提取請求模型"""

    texts: List[str] = Field(..., description="待提取三元組的文本列表")


class TripleExtractionResponse(BaseModel):
    """三元組提取響應模型"""

    triples: List[Triple] = Field(
        default_factory=list, description="提取出的三元組列表"
    )
    text: str = Field(..., description="原始文本")
    entities_count: int = Field(0, description="識別出的實體數量")
    relations_count: int = Field(0, description="識別出的關係數量")


class TripleBatchResponse(BaseModel):
    """三元組批量提取響應模型"""

    results: List[TripleExtractionResponse] = Field(
        default_factory=list, description="每個文本的三元組提取結果"
    )
    total: int = Field(..., description="總文本數")
    processed: int = Field(..., description="成功處理的文本數")
    total_triples: int = Field(0, description="總三元組數")
