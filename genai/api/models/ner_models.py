# 代碼功能說明: NER 實體識別數據模型
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""NER 實體識別數據模型 - 定義 Pydantic Model"""

from typing import List, Optional

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """實體模型"""

    text: str = Field(..., description="實體文本")
    label: str = Field(
        ..., description="實體類型（PERSON, ORG, LOC, DATE, MONEY, PRODUCT, EVENT 等）"
    )
    start: int = Field(..., description="實體在文本中的起始位置")
    end: int = Field(..., description="實體在文本中的結束位置")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度（0-1）")


class NERRequest(BaseModel):
    """NER 請求模型"""

    text: str = Field(..., description="待識別的文本")
    model_type: Optional[str] = Field(
        None, description="指定使用的模型類型（spacy/ollama），不指定則使用配置默認值"
    )


class NERBatchRequest(BaseModel):
    """NER 批量請求模型"""

    texts: List[str] = Field(..., description="待識別的文本列表")
    model_type: Optional[str] = Field(
        None, description="指定使用的模型類型（spacy/ollama），不指定則使用配置默認值"
    )


class NERResponse(BaseModel):
    """NER 響應模型"""

    entities: List[Entity] = Field(default_factory=list, description="識別出的實體列表")
    text: str = Field(..., description="原始文本")
    model_used: str = Field(..., description="實際使用的模型類型")


class NERBatchResponse(BaseModel):
    """NER 批量響應模型"""

    results: List[NERResponse] = Field(default_factory=list, description="每個文本的識別結果")
    total: int = Field(..., description="總文本數")
    processed: int = Field(..., description="成功處理的文本數")
