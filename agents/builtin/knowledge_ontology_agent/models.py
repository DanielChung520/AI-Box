# 代碼功能說明: Knowledge Ontology Agent 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Knowledge Ontology Agent 數據模型定義"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class KnowledgeOntologyAgentRequest(BaseModel):
    """Knowledge Ontology Agent 請求模型"""

    action: str = Field(
        ...,
        description="操作類型（build_from_triples/list_triples/get_entity/get_neighbors/get_subgraph/graphrag_query）",
    )
    # build_from_triples 參數
    triples: Optional[List[Dict[str, Any]]] = Field(
        None, description="三元組列表（build_from_triples 操作需要）"
    )
    file_id: Optional[str] = Field(None, description="文件 ID（可選）")
    user_id: Optional[str] = Field(None, description="用戶 ID（可選）")
    min_confidence: Optional[float] = Field(0.5, description="最小置信度閾值（可選）")
    core_node_threshold: Optional[float] = Field(0.9, description="核心節點閾值（可選）")
    enable_judgment: Optional[bool] = Field(True, description="是否啟用裁決層（可選）")
    # list_triples 參數
    limit: Optional[int] = Field(100, description="返回數量限制（可選）")
    offset: Optional[int] = Field(0, description="偏移量（可選）")
    # get_entity/get_neighbors/get_subgraph 參數
    entity_id: Optional[str] = Field(
        None, description="實體 ID（get_entity/get_neighbors/get_subgraph 操作需要）"
    )
    relation_types: Optional[List[str]] = Field(None, description="關係類型列表（可選）")
    max_depth: Optional[int] = Field(2, description="最大深度（get_subgraph 操作需要）")
    # graphrag_query 參數
    query_type: Optional[str] = Field(
        None, description="查詢類型（entity_retrieval/relation_path/subgraph_extraction）"
    )
    query_params: Optional[Dict[str, Any]] = Field(None, description="查詢參數（可選）")


class KnowledgeOntologyAgentResponse(BaseModel):
    """Knowledge Ontology Agent 響應模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="操作類型")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")


class GraphRAGQueryRequest(BaseModel):
    """GraphRAG 查詢請求模型"""

    query_type: str = Field(
        ...,
        description="查詢類型（entity_retrieval/relation_path/subgraph_extraction）",
    )
    entity_name: Optional[str] = Field(None, description="實體名稱（entity_retrieval 需要）")
    from_entity: Optional[str] = Field(None, description="起始實體（relation_path 需要）")
    to_entity: Optional[str] = Field(None, description="目標實體（relation_path 需要）")
    center_entity: Optional[str] = Field(None, description="中心實體（subgraph_extraction 需要）")
    max_depth: Optional[int] = Field(2, description="最大深度（可選）")
    limit: Optional[int] = Field(50, description="返回數量限制（可選）")
    relation_types: Optional[List[str]] = Field(None, description="關係類型列表（可選）")


class GraphRAGQueryResponse(BaseModel):
    """GraphRAG 查詢響應模型"""

    query_type: str = Field(..., description="查詢類型")
    entities: List[Dict[str, Any]] = Field(default_factory=list, description="實體列表")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="關係列表")
    paths: Optional[List[List[str]]] = Field(None, description="路徑列表（relation_path 查詢）")
    subgraph: Optional[Dict[str, Any]] = Field(None, description="子圖數據（subgraph_extraction 查詢）")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")
