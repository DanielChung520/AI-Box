# 代碼功能說明: KA-Agent MCP 接口 - 知識檢索服務
# 創建日期: 2026-02-14
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-21

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

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from services.api.services.agent_display_config_store_service import (
    AgentDisplayConfigStoreService,
)
from services.api.services.kb_auth_service import KBAuthService
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
    metadata: Optional[Dict[str, Any]] = None


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


def get_kb_auth_svc() -> KBAuthService:
    return KBAuthService()


def get_agent_knowledge_bases(
    agent_id: Optional[str] = None,
    agent_key: Optional[str] = None,
) -> List[str]:
    """根據 agent_id 或 agent_key 獲取該 Agent 關聯的知識庫 ID 列表

    優先級:
    1. 先從 agent_display_configs.knowledge_bases 獲取 KB root IDs
    2. 如果沒有配置，嘗試從 kb_auth_service 獲取
    """
    try:
        store = get_store_service()
        config = store.get_agent_config(
            agent_id=agent_id or "",
            agent_key=agent_key or "",
            tenant_id=None,
        )

        if config and config.knowledge_bases:
            logger.info(
                f"[ka-agent] 從 agent_display_configs 獲取知識庫: "
                f"agent_id={agent_id}, agent_key={agent_key}, kb_count={len(config.knowledge_bases)}"
            )
            return config.knowledge_bases

        kb_auth_svc = get_kb_auth_svc()
        authorized_files = kb_auth_svc.get_authorized_files(
            agent_id=agent_id,
            agent_key=agent_key,
        )

        kb_root_ids: List[str] = []
        for f in authorized_files:
            kb_key = f.get("kb_root_key")
            if kb_key:
                kb_root_ids.append(kb_key)
        kb_root_ids = list(set(kb_root_ids))

        if kb_root_ids:
            logger.info(
                f"[ka-agent] 從 kb_auth_service 獲取知識庫: "
                f"agent_id={agent_id}, agent_key={agent_key}, kb_count={len(kb_root_ids)}"
            )

        return kb_root_ids

    except Exception as e:
        logger.warning(
            f"[ka-agent] 獲取知識庫失敗: agent_id={agent_id}, agent_key={agent_key}, error={e}"
        )
        return []


def get_authorized_file_ids(
    agent_id: Optional[str] = None,
    agent_key: Optional[str] = None,
) -> List[str]:
    """根據 agent_id 或 agent_key 獲取該 Agent 授權的檔案 ID 列表

    返回:
        List[str]: 授權的 file_id 列表
    """
    try:
        kb_auth_svc = get_kb_auth_svc()
        authorized_files = kb_auth_svc.get_authorized_files(
            agent_id=agent_id,
            agent_key=agent_key,
        )

        file_ids: List[str] = []
        for f in authorized_files:
            fid = f.get("file_id")
            if fid:
                file_ids.append(fid)

        logger.info(
            f"[ka-agent] 獲取授權檔案: agent_id={agent_id}, agent_key={agent_key}, "
            f"file_count={len(file_ids)}"
        )

        return file_ids  # type: ignore[return-value]

    except Exception as e:
        logger.warning(
            f"[ka-agent] 獲取授權檔案失敗: agent_id={agent_id}, agent_key={agent_key}, error={e}"
        )
        return []


async def execute_hybrid_search(
    query: str, folder_ids: List[str], top_k: int
) -> List[Dict[str, Any]]:
    """使用向量服務執行混合檢索"""
    try:
        from services.api.services.embedding_service import get_embedding_service
        from services.api.services.qdrant_vector_store_service import (
            get_qdrant_vector_store_service,
        )

        emb_svc = get_embedding_service()
        vec_svc = get_qdrant_vector_store_service()

        # 生成 embedding
        q_emb = await emb_svc.generate_embedding(text=query)

        # 獲取每個文件夾中的文件 ID
        import httpx

        file_ids = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for folder_id in folder_ids:
                try:
                    resp = await client.get(
                        f"http://localhost:8000/api/v1/knowledge-bases/folders/{folder_id}/files",
                        params={"user_id": "system"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        files = data.get("data", {}).get("items", [])
                        for f in files:
                            if f.get("vector_count", 0) > 0:
                                file_ids.append(f.get("file_id"))
                except Exception as e:
                    logger.warning(f"[ka-agent] 獲取文件夾 {folder_id} 文件失敗: {e}")

        if not file_ids:
            logger.warning("[ka-agent] 沒有找到已向量化的文件")
            return []

        # 對每個文件進行向量檢索
        all_results = []
        for file_id in file_ids[:20]:
            try:
                hits = vec_svc.query_vectors(
                    query_embedding=q_emb,
                    file_id=file_id,
                    limit=top_k,
                )
                for h in hits:
                    h["file_id"] = file_id
                    all_results.append(h)
            except Exception as e:
                logger.warning(f"[ka-agent] 檢索文件 {file_id} 失敗: {e}")

        logger.info(f"[ka-agent] 向量檢索完成: {len(all_results)} 結果")

        # 對於短查詢（可能是代碼）或信心度低的情況，嘗試關鍵字搜尋
        min_confidence_threshold = 0.4
        top_score = all_results[0].get("score", 0) if all_results else 0
        is_short_query = len(query) <= 15

        if not all_results or top_score < min_confidence_threshold or is_short_query:
            if not all_results:
                reason = "無結果"
            elif top_score < min_confidence_threshold:
                reason = f"信心度過低 ({top_score:.2f})"
            else:
                reason = "短查詢"
            logger.info(f"[ka-agent] 向量搜尋 {reason}，嘗試關鍵字搜尋: {query}")
            keyword_results = await execute_keyword_search(query, folder_ids, top_k)

            if keyword_results:
                # 合併結果：關鍵字結果排在前面
                all_results = keyword_results + all_results

        return all_results

    except Exception as e:
        logger.warning(f"[ka-agent] 混合檢索失敗: {e}")
        # 嘗試關鍵字搜尋作為 fallback
        try:
            keyword_results = await execute_keyword_search(query, folder_ids, top_k)
            return keyword_results
        except Exception as kw_err:
            logger.warning(f"[ka-agent] 關鍵字搜尋也失敗: {kw_err}")
            return []


async def execute_keyword_search(
    query: str, folder_ids: List[str], top_k: int
) -> List[Dict[str, Any]]:
    """使用關鍵字執行精確檢索（fallback 機制）"""
    try:
        from services.api.services.qdrant_vector_store_service import (
            get_qdrant_vector_store_service,
        )

        vec_svc = get_qdrant_vector_store_service()

        # 獲取每個文件夾中的文件 ID
        import httpx

        file_ids = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            for folder_id in folder_ids:
                try:
                    resp = await client.get(
                        f"http://localhost:8000/api/v1/knowledge-bases/folders/{folder_id}/files",
                        params={"user_id": "system"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        files = data.get("data", {}).get("items", [])
                        for f in files:
                            if f.get("vector_count", 0) > 0:
                                file_ids.append(f.get("file_id"))
                except Exception as e:
                    logger.warning(f"[ka-agent] 獲取文件夾 {folder_id} 文件失敗: {e}")

        if not file_ids:
            logger.warning("[ka-agent] 沒有找到已向量化的文件")
            return []

        # 對每個文件進行關鍵字檢索
        all_results = []
        query_lower = query.lower()

        for file_id in file_ids[:20]:
            try:
                # 獲取該文件的所有 chunks
                chunks = vec_svc.get_vectors_by_file_id(
                    file_id=file_id,
                    limit=1000,
                    with_vector=False,
                )

                # 本地過濾：找出包含關鍵字的 chunks
                for chunk in chunks:
                    payload = chunk.get("payload", {})
                    chunk_text = payload.get("chunk_text", "")
                    if chunk_text and query_lower in chunk_text.lower():
                        # 計算簡單的相關度分數（關鍵字出現次數）
                        count = chunk_text.lower().count(query_lower)
                        relevance_score = min(count / 10.0, 1.0)  # 最高 1.0

                        all_results.append(
                            {
                                "id": chunk.get("id"),
                                "score": relevance_score,
                                "distance": 1.0 - relevance_score,
                                "document": chunk_text,
                                "source": "keyword",
                                "metadata": {
                                    "file_id": file_id,
                                    "chunk_index": payload.get("chunk_index"),
                                    "chunk_size": payload.get("chunk_size"),
                                    "task_id": payload.get("task_id"),
                                    "user_id": payload.get("user_id"),
                                },
                            }
                        )
            except Exception as e:
                logger.warning(f"[ka-agent] 關鍵字檢索文件 {file_id} 失敗: {e}")

        # 按相關度排序
        all_results.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"[ka-agent] 關鍵字檢索完成: {len(all_results)} 結果")
        return all_results[:top_k]

    except Exception as e:
        logger.warning(f"[ka-agent] 關鍵字檢索失敗: {e}")
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
            caller_agent_key = None
            caller_agent_id = None

            if request.metadata:
                caller_agent_key = request.metadata.get("caller_agent_key")
                caller_agent_id = request.metadata.get("caller_agent_id")

            # 優先使用 _key，其次用 agent_id
            actual_key = caller_agent_key
            actual_id = caller_agent_id or request.agent_id

            logger.info(
                f"[ka-agent] 查詢知識庫: request.agent_id={request.agent_id}, caller_agent_key={caller_agent_key}, caller_agent_id={caller_agent_id}, actual_key={actual_key}, actual_id={actual_id}"
            )

            kb_ids = get_agent_knowledge_bases(
                agent_id=actual_id if actual_id else None,
                agent_key=actual_key if actual_key else None,
            )

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

        # 使用 HybridRAG 執行混合檢索
        vector_results = await execute_hybrid_search(request.query, folder_ids, top_k)

        graph_results = []
        if include_graph:
            graph_results = await execute_graph_search(request.query, folder_ids)

        merged_results = []

        # 預先查詢 file_id -> filename 映射
        file_id_to_name = {}
        if folder_ids:
            try:
                from database.arangodb import ArangoDBClient

                client = ArangoDBClient()
                db = client.db
                if db:
                    cursor = db.aql.execute(
                        """
                    FOR file IN file_metadata
                    FILTER file.folder_id IN @folder_ids
                    RETURN {file_id: file.file_id, filename: file.filename}
                    """,
                        bind_vars={"folder_ids": folder_ids},
                    )
                    for f in cursor:
                        file_id_to_name[f["file_id"]] = f["filename"]
            except Exception:
                pass

        for r in vector_results:
            meta = r.get("metadata", {})
            fid = meta.get("file_id", "")
            result_source = r.get("source", "vector")
            merged_results.append(
                {
                    "file_id": fid,
                    "filename": file_id_to_name.get(fid, ""),
                    "chunk_id": str(meta.get("chunk_index", "")),
                    "content": r.get("document", "")[:500],
                    "confidence": r.get("score", 0.0),
                    "source": result_source,
                    "metadata": meta,
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

        # 按信心度排序，但優先顯示關鍵字結果
        def sort_key(x):
            is_keyword = 1 if x.get("source") == "keyword" else 0
            return (is_keyword, x.get("confidence", 0))

        merged_results.sort(key=sort_key, reverse=True)
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
                                        1 for f in files if f.get("vector_count", 0) > 0
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
