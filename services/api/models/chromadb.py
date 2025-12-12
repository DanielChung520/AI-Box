# 代碼功能說明: ChromaDB API 請求/響應模型
# 創建日期: 2025-11-25 21:40 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 21:40 (UTC+8)

"""ChromaDB API 請求/響應模型定義"""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, model_validator


class CollectionCreateRequest(BaseModel):
    """創建集合請求"""

    name: str = Field(..., description="集合名稱")
    metadata: Optional[Dict[str, Any]] = Field(None, description="集合元數據")
    embedding_dimension: Optional[int] = Field(None, description="嵌入向量維度")


class CollectionResponse(BaseModel):
    """集合響應"""

    name: str
    metadata: Optional[Dict[str, Any]] = None
    count: int = 0


class DocumentAddRequest(BaseModel):
    """添加文檔請求"""

    ids: Union[str, List[str]] = Field(..., description="文檔 ID 或 ID 列表")
    embeddings: Optional[Union[List[List[float]], List[float]]] = Field(
        None, description="嵌入向量或向量列表"
    )
    metadatas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        None, description="元數據字典或字典列表"
    )
    documents: Optional[Union[str, List[str]]] = Field(
        None, description="文檔文本或文本列表"
    )
    auto_embed: bool = Field(
        False, description="若未提供 embeddings，使用默認嵌入提供者（需 documents）"
    )
    embedding_model: Optional[str] = Field(
        None,
        description="覆寫嵌入模型（預設見 config.services.ollama.embedding_model）",
    )


class DocumentUpdateRequest(BaseModel):
    """更新文檔請求"""

    embeddings: Optional[Union[List[List[float]], List[float]]] = Field(
        None, description="嵌入向量或向量列表"
    )
    metadatas: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = Field(
        None, description="元數據字典或字典列表"
    )
    documents: Optional[Union[str, List[str]]] = Field(
        None, description="文檔文本或文本列表"
    )


class QueryRequest(BaseModel):
    """向量檢索請求"""

    query_embeddings: Optional[Union[List[List[float]], List[float]]] = Field(
        None, description="查詢嵌入向量"
    )
    query_texts: Optional[Union[str, List[str]]] = Field(
        None, description="查詢文本（將使用集合的嵌入函數）"
    )
    n_results: int = Field(10, ge=1, le=100, description="返回結果數量")
    where: Optional[Dict[str, Any]] = Field(None, description="元數據過濾條件")
    where_document: Optional[Dict[str, Any]] = Field(
        None, description="文檔內容過濾條件"
    )
    include: Optional[List[str]] = Field(
        None,
        description="包含的字段列表 ['documents', 'metadatas', 'embeddings', 'distances']",
    )

    @model_validator(mode="after")
    def validate_query_input(self):
        """確保至少提供一種查詢方式"""
        if self.query_embeddings is None and self.query_texts is None:
            raise ValueError("Either query_embeddings or query_texts must be provided")
        return self


class DocumentItem(BaseModel):
    """文檔項目"""

    id: str
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    document: Optional[str] = None


class QueryResponse(BaseModel):
    """查詢響應"""

    ids: List[List[str]]
    embeddings: Optional[List[List[List[float]]]] = None
    metadatas: Optional[List[List[Dict[str, Any]]]] = None
    documents: Optional[List[List[str]]] = None
    distances: Optional[List[List[float]]] = None


class DocumentResponse(BaseModel):
    """文檔響應"""

    ids: List[str]
    embeddings: Optional[List[List[float]]] = None
    metadatas: Optional[List[Dict[str, Any]]] = None
    documents: Optional[List[str]] = None


class BatchAddRequest(BaseModel):
    """批量添加文檔請求"""

    items: List[DocumentItem] = Field(..., description="文檔項目列表")
    batch_size: Optional[int] = Field(None, ge=1, le=1000, description="批次大小")
    auto_embed: bool = Field(
        False, description="缺少 embedding 的項目將由嵌入提供者補齊（需 document）"
    )
    embedding_model: Optional[str] = Field(None, description="覆寫嵌入模型")


class BatchAddResponse(BaseModel):
    """批量添加響應"""

    total: int
    success: int
    failed: int
    errors: List[Dict[str, Any]] = []
