# -*- coding: utf-8 -*-
"""
Data-Agent-JP mmMasterRAG API 路由

端點：
- POST /api/v1/mm-master/rag/search - 混合檢索
- POST /api/v1/mm-master/rag/semantic-search - 語意搜尋

建立日期: 2026-02-10
建立人: Daniel Chung
"""

import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException

from database.qdrant.mm_master_rag_client import (
    get_mm_master_rag_client,
    ItemEmbedding,
    WarehouseEmbedding,
    WorkstationEmbedding,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    """語意搜尋請求"""

    query: str
    query_type: Optional[str] = None  # "item", "warehouse", "workstation", "all"
    limit: int = 10
    score_threshold: float = 0.5


class HybridSearchRequest(BaseModel):
    """混合搜尋請求"""

    query: str
    limit: int = 10


class SearchResponse(BaseModel):
    """搜尋響應"""

    status: str
    query: str
    results: List[Dict[str, Any]]
    count: int


@router.post("/search")
async def semantic_search(request: SemanticSearchRequest) -> SearchResponse:
    """
    語意搜尋

    Args:
        request: 搜尋請求

    Returns:
        SearchResponse: 搜尋結果
    """
    try:
        client = get_mm_master_rag_client()

        results = client.search(
            query_vector=[],  # 需要填入實際的向量
            query_type=request.query_type or "all",
            limit=request.limit,
            score_threshold=request.score_threshold,
        )

        return SearchResponse(
            status="success",
            query=request.query,
            results=results,
            count=len(results),
        )
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/hybrid-search")
async def hybrid_search(request: HybridSearchRequest) -> SearchResponse:
    """
    混合搜尋（關鍵詞 + 語意）

    Args:
        request: 混合搜尋請求

    Returns:
        SearchResponse: 搜尋結果
    """
    try:
        client = get_mm_master_rag_client()

        results = client.hybrid_search(
            text=request.query,
            embedding_model=None,  # 需要注入實際的 embedding model
            limit=request.limit,
        )

        return SearchResponse(
            status="success",
            query=request.query,
            results=results,
            count=len(results),
        )
    except Exception as e:
        logger.error(f"Hybrid search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Hybrid search failed: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康檢查

    Returns:
        dict: 健康狀態
    """
    try:
        client = get_mm_master_rag_client()
        health = client.health_check()
        return health
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    取得統計資訊

    Returns:
        dict: 統計資訊
    """
    try:
        client = get_mm_master_rag_client()
        counts = client.count_by_type()

        return {
            "status": "success",
            "data": {
                "total_documents": sum(counts.values()),
                "by_type": counts,
            },
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
