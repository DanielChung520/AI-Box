# 代碼功能說明: KA-Agent MCP 接口 - 知識檢索服務
# 創建日期: 2026-02-14
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-14

"""
KA-Agent MCP 接口 - 提供知識庫檢索、統計等功能

接口:
- knowledge.query: 混合檢索（向量 + 圖譜）
- ka.stats: 知識庫統計
- ka.list: 列出知識庫
"""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.core.response import APIResponse
from services.api.models.agent_display_config import AgentConfig
from services.api.services.agent_display_config_store_service import (
    AgentDisplayConfigStoreService,
)
from system.security.dependencies import get_current_user
from system.security.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class KnowledgeQueryRequest(BaseModel):
    request_id: str
    query: str
    agent_id: str
    user_id: str
    session_id: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class KnowledgeQueryResult(BaseModel):
    file_id: str
    filename: str
    chunk_id: str
    content: str
    confidence: float
    source: str
    metadata: Optional[Dict[str, Any]] = None


class KnowledgeQueryResponse(BaseModel):
    request_id: str
    success: bool
    results: List[KnowledgeQueryResult]
    total: int
    query_time_ms: int
    audit_log_id: Optional[str] = None


class KnowledgeBaseStatsItem(BaseModel):
    kb_id: str
    name: str
    total_files: int
    vectorized_files: int


class KnowledgeBaseStatsResponse(BaseModel):
    success: bool
    knowledge_bases: List[KnowledgeBaseStatsItem]
    total_files: int
    total_vectorized: int
    audit_log_id: Optional[str] = None


class KnowledgeBaseListItem(BaseModel):
    kb_id: str
    name: str
    domain: str
    domain_name: str
    folder_count: int
    file_count: int
    created_at: str


class KnowledgeBaseListResponse(BaseModel):
    success: bool
    items: List[KnowledgeBaseListItem]
    total: int


def get_store_service() -> AgentDisplayConfigStoreService:
    return AgentDisplayConfigStoreService()


def get_agent_knowledge_bases(agent_id: str) -> List[str]:
    """獲取 Agent 配置的 Knowledge Base 列表"""
    try:
        store = get_store_service()
        agent_config = store.get_agent_config(agent_id)
        if agent_config and hasattr(agent_config, "knowledge_bases"):
            return agent_config.knowledge_bases or []
        return []
    except Exception as e:
        logger.warning(f"[ka-agent] 獲取 Agent 知識庫配置失敗: {e}")
        return []


async def resolve_kb_to_folders(kb_ids: List[str], user_id: str) -> Dict[str, Any]:
    """將 Knowledge Base ID 列表解析為 Folder 列表"""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        folder_ids = []
        kb_info = []

        for kb_id in kb_ids:
            try:
                response = await client.get(
                    f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}/folders",
                    params={"user_id": user_id},
                )
                if response.status_code == 200:
                    data = response.json()
                    folders = data.get("data", {}).get("items", [])
                    for folder in folders:
                        folder_id = folder.get("id")
                        if folder_id:
                            folder_ids.append(folder_id)
                    kb_name = folders[0].get("name", kb_id) if folders else kb_id
                    kb_info.append(
                        {
                            "kb_id": kb_id,
                            "name": kb_name,
                            "folders": [f.get("id") for f in folders],
                        }
                    )
            except Exception as e:
                logger.warning(f"[ka-agent] 查詢知識庫 {kb_id} 失敗: {e}")

        return {
            "folder_ids": folder_ids,
            "kb_info": kb_info,
            "task_ids": [f"kb_{fid}" for fid in folder_ids],
        }


async def execute_vector_search(
    query: str, task_ids: List[str], top_k: int
) -> List[Dict[str, Any]]:
    """執行向量檢索"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/vector/search",
                json={
                    "query": query,
                    "task_ids": task_ids,
                    "top_k": top_k,
                },
            )
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
    except Exception as e:
        logger.warning(f"[ka-agent] 向量檢索失敗: {e}")
        return []


async def execute_graph_search(query: str, folder_ids: List[str]) -> List[Dict[str, Any]]:
    """執行圖譜檢索"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/kg/search",
                json={"query": query, "folder_ids": folder_ids},
            )
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
    except Exception as e:
        logger.warning(f"[ka-agent] 圖譜檢索失敗: {e}")
        return []


async def log_audit(
    user_id: str,
    agent_id: str,
    action: str,
    details: Dict[str, Any],
) -> str:
    """記錄審計日誌"""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/audit/log",
                json={
                    "user_id": user_id,
                    "action": action,
                    "agent_id": agent_id,
                    "details": details,
                },
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("audit_id", str(uuid.uuid4()))
    except Exception as e:
        logger.warning(f"[ka-agent] 審計日誌記錄失敗: {e}")
    return str(uuid.uuid4())


@router.post("/knowledge/query", response_model=KnowledgeQueryResponse)
async def knowledge_query(
    request: KnowledgeQueryRequest,
    current_user: User = Depends(get_current_user),
) -> KnowledgeQueryResponse:
    """
    知識庫混合檢索接口

    執行向量檢索 + 圖譜檢索，返回混合排序結果
    """
    start_time = time.time()

    try:
        kb_ids = request.options.get("kb_scope") if request.options else None

        if not kb_ids:
            kb_ids = get_agent_knowledge_bases(request.agent_id)

        if not kb_ids:
            return KnowledgeQueryResponse(
                request_id=request.request_id,
                success=True,
                results=[],
                total=0,
                query_time_ms=int((time.time() - start_time) * 1000),
                audit_log_id=await log_audit(
                    request.user_id,
                    request.agent_id,
                    "KNOWLEDGE_QUERY_EMPTY",
                    {"reason": "no_knowledge_bases_configured"},
                ),
            )

        storage_scope = await resolve_kb_to_folders(kb_ids, request.user_id)
        folder_ids = storage_scope["folder_ids"]
        task_ids = storage_scope["task_ids"]

        if not task_ids:
            return KnowledgeQueryResponse(
                request_id=request.request_id,
                success=True,
                results=[],
                total=0,
                query_time_ms=int((time.time() - start_time) * 1000),
            )

        top_k = request.options.get("top_k", 10) if request.options else 10
        include_graph = request.options.get("include_graph", True) if request.options else True

        vector_results = await execute_vector_search(request.query, task_ids, top_k)

        graph_results = []
        if include_graph:
            graph_results = await execute_graph_search(request.query, folder_ids)

        merged_results = []

        for r in vector_results:
            merged_results.append(
                {
                    "file_id": r.get("file_id", ""),
                    "filename": r.get("filename", ""),
                    "chunk_id": r.get("chunk_id", ""),
                    "content": r.get("content", "")[:500],
                    "confidence": r.get("score", 0.0),
                    "source": "vector",
                    "metadata": r.get("metadata", {}),
                }
            )

        for r in graph_results:
            merged_results.append(
                {
                    "file_id": r.get("file_id", ""),
                    "filename": r.get("filename", ""),
                    "chunk_id": r.get("entity_id", ""),
                    "content": r.get("content", "")[:500],
                    "confidence": r.get("confidence", 0.0),
                    "source": "graph",
                    "metadata": r.get("metadata", {}),
                }
            )

        merged_results.sort(key=lambda x: x["confidence"], reverse=True)
        merged_results = merged_results[:top_k]

        query_time_ms = int((time.time() - start_time) * 1000)

        audit_id = await log_audit(
            request.user_id,
            request.agent_id,
            "KNOWLEDGE_QUERY",
            {
                "query": request.query,
                "kb_count": len(kb_ids),
                "result_count": len(merged_results),
                "query_time_ms": query_time_ms,
            },
        )

        return KnowledgeQueryResponse(
            request_id=request.request_id,
            success=True,
            results=[KnowledgeQueryResult(**r) for r in merged_results],
            total=len(merged_results),
            query_time_ms=query_time_ms,
            audit_log_id=audit_id,
        )

    except Exception as e:
        logger.error(f"[ka-agent] knowledge.query 失敗: {e}", exc_info=True)
        return KnowledgeQueryResponse(
            request_id=request.request_id,
            success=False,
            results=[],
            total=0,
            query_time_ms=int((time.time() - start_time) * 1000),
        )


@router.get("/ka/stats", response_model=KnowledgeBaseStatsResponse)
async def get_knowledge_base_stats(
    agent_id: str = Query(..., description="Agent ID"),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseStatsResponse:
    """
    獲取 Agent 關聯的 Knowledge Base 統計信息
    """
    try:
        kb_ids = get_agent_knowledge_bases(agent_id)

        if not kb_ids:
            return KnowledgeBaseStatsResponse(
                success=True,
                knowledge_bases=[],
                total_files=0,
                total_vectorized=0,
            )

        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            stats = []
            total_files = 0
            total_vectorized = 0

            for kb_id in kb_ids:
                try:
                    folders_response = await client.get(
                        f"http://localhost:8000/api/v1/knowledge-bases/{kb_id}/folders",
                        params={"user_id": current_user.user_id},
                    )

                    kb_name = kb_id
                    if folders_response.status_code == 200:
                        data = folders_response.json()
                        folders = data.get("data", {}).get("items", [])
                        kb_name = folders[0].get("name", kb_id) if folders else kb_id

                        kb_total = 0
                        kb_vectorized = 0

                        for folder in folders:
                            folder_id = folder.get("id")
                            if folder_id:
                                files_response = await client.get(
                                    f"http://localhost:8000/api/v1/knowledge-bases/folders/{folder_id}/files",
                                    params={"user_id": current_user.user_id},
                                )
                                if files_response.status_code == 200:
                                    files_data = files_response.json()
                                    files = files_data.get("data", {}).get("items", [])
                                    kb_total += len(files)
                                    kb_vectorized += sum(
                                        1
                                        for f in files
                                        if f.get("hasS3") and f.get("vectorCount", 0) > 0
                                    )

                        stats.append(
                            {
                                "kb_id": kb_id,
                                "name": kb_name,
                                "total_files": kb_total,
                                "vectorized_files": kb_vectorized,
                            }
                        )
                        total_files += kb_total
                        total_vectorized += kb_vectorized

                except Exception as e:
                    logger.warning(f"[ka-agent] 統計知識庫 {kb_id} 失敗: {e}")

            audit_id = await log_audit(
                current_user.user_id, agent_id, "KNOWLEDGE_STATS", {"kb_count": len(kb_ids)}
            )

            return KnowledgeBaseStatsResponse(
                success=True,
                knowledge_bases=[KnowledgeBaseStatsItem(**s) for s in stats],
                total_files=total_files,
                total_vectorized=total_vectorized,
                audit_log_id=audit_id,
            )

    except Exception as e:
        logger.error(f"[ka-agent] ka.stats 失敗: {e}", exc_info=True)
        return KnowledgeBaseStatsResponse(
            success=False, knowledge_bases=[], total_files=0, total_vectorized=0
        )


@router.get("/ka/list", response_model=KnowledgeBaseListResponse)
async def list_knowledge_bases(
    agent_id: str = Query(..., description="Agent ID"),
    current_user: User = Depends(get_current_user),
) -> KnowledgeBaseListResponse:
    """
    列出 Agent 可訪問的 Knowledge Base
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://localhost:8000/api/v1/knowledge-bases",
                params={"user_id": current_user.user_id},
            )

            if response.status_code != 200:
                return KnowledgeBaseListResponse(success=False, items=[], total=0)

            data = response.json()
            items = data.get("data", {}).get("items", [])

            agent_kb_ids = set(get_agent_knowledge_bases(agent_id))

            result_items = []
            for item in items:
                kb_id = item.get("id")
                if kb_id in agent_kb_ids or not agent_kb_ids:
                    result_items.append(
                        {
                            "kb_id": kb_id,
                            "name": item.get("name", ""),
                            "domain": item.get("domain", ""),
                            "domain_name": item.get("domain_name", ""),
                            "folder_count": item.get("folder_count", 0),
                            "file_count": item.get("file_count", 0),
                            "created_at": item.get("created_at", ""),
                        }
                    )

            return KnowledgeBaseListResponse(
                success=True, items=result_items, total=len(result_items)
            )

    except Exception as e:
        logger.error(f"[ka-agent] ka.list 失敗: {e}", exc_info=True)
        return KnowledgeBaseListResponse(success=False, items=[], total=0)
