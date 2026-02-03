# 代碼功能說明: KA-Agent (Knowledge Architect Agent) 數據模型
# 創建日期: 2026-01-25
# 創建人: Daniel Chung

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


class KARequest(BaseModel):
    """KA-Agent 通用請求模型"""

    action: str = Field(
        ..., description="操作類型: knowledge.query, ka.lifecycle, ka.list, ka.retrieve"
    )
    query: Optional[str] = Field(None, description="語義關鍵字")
    ka_scope: Optional[List[str]] = Field(None, description="知識資產 ID 列表")
    top_k: int = Field(default=10, description="返回數量")
    query_type: Literal["semantic", "graph", "hybrid"] = Field(
        default="hybrid", description="查詢類型"
    )

    # 生命週期與管理參數
    ka_id: Optional[str] = Field(None, description="目標資產 ID")
    target_state: Optional[str] = Field(None, description="目標狀態 (Active/Deprecated/Archived)")
    version: Optional[str] = Field(None, description="版本號")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")

    # 檢索過濾（Domain / Major）
    domain: Optional[str] = Field(None, description="知識領域過濾，如 domain-enterprise")
    major: Optional[str] = Field(None, description="專業層過濾，如 major-manufacture")
    # 管理流程用於註冊的 file_id（上架時對應已上傳文件）
    file_id: Optional[str] = Field(None, description="文件 ID（上架時由上傳流程提供）")


class KAResult(BaseModel):
    """檢索結果項"""

    content: str
    ka_id: str
    version: str
    confidence_hint: float
    source: str  # vector, graph, hybrid
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KAResponse(BaseModel):
    """KA-Agent 響應模型"""

    success: bool
    message: str
    results: List[KAResult] = Field(default_factory=list)
    total: int = 0
    query_time_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict, description="響應元數據，如 Todo List")
    error: Optional[str] = None
