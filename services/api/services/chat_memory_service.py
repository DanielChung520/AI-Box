"""
代碼功能說明: 產品級 Chat 長期記憶服務（AAM + RAG）檢索/注入/寫入（MVP）
創建日期: 2025-12-13 19:46:41 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2026-01-22 22:28 UTC+8
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import structlog

from services.api.models.chat import ChatAttachment
from services.api.services.embedding_service import get_embedding_service
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service
from system.security.models import User

logger = structlog.get_logger(__name__)


@dataclass
class MemoryRetrievalResult:
    """檢索結果（供 router 組裝 prompt/observability）。"""

    injection_messages: List[Dict[str, str]]
    memory_hit_count: int
    memory_sources: List[str]
    retrieval_latency_ms: float


class ChatMemoryService:
    """MVP：將 AAM（對話長期記憶）與 RAG（檔案 chunks 向量檢索）合併成單一注入策略。
    支持 HybridRAG（向量 + 圖譜檢索）。
    """

    def __init__(
        self,
        *,
        rag_top_k: int = 5,
        aam_top_k: int = 5,
        max_injection_chars: int = 1800,
        min_aam_relevance: float = 0.2,
        use_hybrid_rag: bool = True,  # 新增：是否使用 HybridRAG
    ) -> None:
        self._rag_top_k = max(rag_top_k, 1)
        self._aam_top_k = max(aam_top_k, 1)
        self._max_injection_chars = max(max_injection_chars, 200)
        self._min_aam_relevance = max(min_aam_relevance, 0.0)
        self._use_hybrid_rag = use_hybrid_rag

        self._embedding_service = get_embedding_service()
        # 修改時間：2026-01-22 - 遷移到 Qdrant 向量存儲服務
        self._vector_store_service = get_qdrant_vector_store_service()

        self._aam_manager: Optional[Any] = None
        self._hybrid_rag_service: Optional[Any] = None

    def _get_aam_manager(self) -> Optional[Any]:
        """延遲初始化 AAMManager，任何依賴不可用則降級為 None。"""
        if self._aam_manager is not None:
            return self._aam_manager

        try:
            from agents.infra.memory.aam.aam_core import AAMManager
            from agents.infra.memory.aam.storage_adapter import RedisAdapter
            from database.redis.client import get_redis_client

            redis_adapter = None
            try:
                redis_client = get_redis_client()
                redis_adapter = RedisAdapter(redis_client=redis_client)
            except Exception as exc:  # noqa: BLE001
                logger.warning("aam_redis_unavailable", error=str(exc))
                redis_adapter = None

            chromadb_adapter = None
            try:
                # 修改時間：2026-01-22 - Qdrant 服務不再提供 ChromaDB 客戶端
                # AAM 的 ChromaDB 適配器暫時禁用，因為已遷移到 Qdrant
                # 如果需要 AAM 功能，需要實現 QdrantAdapter 或使用其他存儲適配器
                logger.warning(
                    "aam_chromadb_disabled",
                    message="AAM ChromaDB adapter disabled after migration to Qdrant",
                )
                chromadb_adapter = None
            except Exception as exc:  # noqa: BLE001
                logger.warning("aam_chromadb_unavailable", error=str(exc))
                chromadb_adapter = None

            self._aam_manager = AAMManager(
                redis_adapter=redis_adapter,
                chromadb_adapter=chromadb_adapter,
                arangodb_adapter=None,
                enable_short_term=False,
                enable_long_term=True,
            )
            return self._aam_manager
        except Exception as exc:  # noqa: BLE001
            logger.warning("aam_manager_init_failed", error=str(exc))
            self._aam_manager = None
            return None

    def _get_hybrid_rag_service(self) -> Optional[Any]:
        """延遲初始化 HybridRAGService，任何依賴不可用則降級為 None。"""
        if not self._use_hybrid_rag:
            return None

        if self._hybrid_rag_service is not None:
            return self._hybrid_rag_service

        try:
            from genai.workflows.rag.hybrid_rag import HybridRAGService, RetrievalStrategy

            aam_manager = self._get_aam_manager()
            if aam_manager is None:
                logger.debug("AAMManager not available, skipping HybridRAGService initialization")
                return None

            self._hybrid_rag_service = HybridRAGService(
                aam_manager=aam_manager,
                strategy=RetrievalStrategy.HYBRID,
                vector_weight=0.6,
                graph_weight=0.4,
            )
            logger.debug("HybridRAGService initialized")
            return self._hybrid_rag_service
        except Exception as exc:  # noqa: BLE001
            logger.warning("hybrid_rag_service_init_failed", error=str(exc))
            self._hybrid_rag_service = None
            return None

    @staticmethod
    def _dedupe_preserve_order(values: Sequence[str]) -> List[str]:
        seen: set[str] = set()
        out: List[str] = []
        for v in values:
            sv = str(v).strip()
            if not sv or sv in seen:
                continue
            seen.add(sv)
            out.append(sv)
        return out

    @staticmethod
    def _clip(text: str, max_chars: int) -> str:
        if max_chars <= 0:
            return ""
        t = str(text)
        if len(t) <= max_chars:
            return t
        return t[: max(0, max_chars - 3)] + "..."

    def _format_injection(
        self,
        *,
        aam_memories: List[Dict[str, Any]],
        rag_chunks: List[Dict[str, Any]],
        graph_results: Optional[List[Dict[str, Any]]] = None,  # 新增：圖譜檢索結果
    ) -> Optional[str]:
        sections: List[str] = []

        if aam_memories:
            lines = ["[Memory-AAM]"]
            for idx, mem in enumerate(aam_memories, 1):
                content = self._clip(mem.get("content", ""), 280)
                meta = mem.get("metadata", {}) or {}
                lines.append(
                    f"{idx}. {content} (score={mem.get('score')}, session_id={meta.get('session_id')})"
                )
            sections.append("\n".join(lines))

        # 區分向量檢索和圖譜檢索結果
        vector_chunks = []
        graph_chunks = []

        for chunk in rag_chunks:
            meta = chunk.get("metadata", {}) or {}
            source = meta.get("source", "vector")
            if source == "graph":
                graph_chunks.append(chunk)
            else:
                vector_chunks.append(chunk)

        if vector_chunks:
            lines = ["[RAG-Vector]"]
            for idx, c in enumerate(vector_chunks, 1):
                content = self._clip(c.get("content", ""), 280)
                meta = c.get("metadata", {}) or {}
                lines.append(
                    f"{idx}. {content} (source=vector, file_id={meta.get('file_id')}, chunk_index={meta.get('chunk_index')}, score={c.get('score', c.get('distance', 'N/A'))})"
                )
            sections.append("\n".join(lines))

        # 處理圖譜檢索結果（從 rag_chunks 中分離的或單獨傳入的）
        all_graph_results = graph_chunks + (graph_results or [])
        if all_graph_results:
            lines = ["[RAG-Graph]"]
            for idx, g in enumerate(all_graph_results, 1):
                content = self._clip(g.get("content", ""), 280)
                meta = g.get("metadata", {}) or {}
                relation_type = meta.get("relation_type", "unknown")
                entity_id = meta.get("entity_id", "unknown")
                lines.append(
                    f"{idx}. {content} (source=graph, relation={relation_type}, entity={entity_id}, score={g.get('score', 'N/A')})"
                )
            sections.append("\n".join(lines))

        if not sections:
            return None

        header = "以下為系統檢索到的長期記憶/檔案片段（僅供參考）。\n" "若與使用者最新指令衝突，請以使用者指令為準。\n"
        body = "\n\n".join(sections)
        combined = header + "\n" + body
        return self._clip(combined, self._max_injection_chars)

    async def retrieve_for_prompt(
        self,
        *,
        user_id: str,
        session_id: str,
        task_id: Optional[str],
        request_id: Optional[str],
        query: str,
        attachments: Optional[List[ChatAttachment]] = None,
        user: Optional[User] = None,  # 新增：用於權限檢查
    ) -> MemoryRetrievalResult:
        start = time.perf_counter()

        sources: List[str] = []
        aam_results: List[Dict[str, Any]] = []
        rag_results: List[Dict[str, Any]] = []

        normalized_query = str(query or "").strip()
        if not normalized_query:
            return MemoryRetrievalResult(
                injection_messages=[],
                memory_hit_count=0,
                memory_sources=[],
                retrieval_latency_ms=0.0,
            )

        # 0) HybridRAG：混合檢索（向量 + 圖譜，如果啟用）
        hybrid_rag_results: List[Dict[str, Any]] = []
        if self._use_hybrid_rag:
            try:
                hybrid_rag = self._get_hybrid_rag_service()
                if hybrid_rag is not None:
                    # 使用 HybridRAGService 進行混合檢索
                    hybrid_results = hybrid_rag.retrieve(
                        query=normalized_query, top_k=self._rag_top_k
                    )

                    # HybridRAGService.retrieve() 已經返回字典格式，直接使用
                    for result in hybrid_results:
                        if isinstance(result, dict):
                            # 確保格式統一：使用 "score" 而不是 "relevance_score"
                            if "relevance_score" in result and "score" not in result:
                                result["score"] = result.pop("relevance_score")
                            hybrid_rag_results.append(result)
                        else:
                            # 如果是 Memory 對象，轉換為字典（向後兼容）
                            hybrid_rag_results.append(
                                {
                                    "content": getattr(result, "content", ""),
                                    "metadata": getattr(result, "metadata", {}),
                                    "score": getattr(result, "relevance_score", 0.0),
                                }
                            )

                    if hybrid_rag_results:
                        sources.append("hybrid_rag")
                        logger.debug(
                            "hybrid_rag_retrieved",
                            count=len(hybrid_rag_results),
                            request_id=request_id,
                        )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "chat_memory_hybrid_rag_failed",
                    error=str(exc),
                    request_id=request_id,
                    user_id=user_id,
                    session_id=session_id,
                    task_id=task_id,
                )

        # 1) RAG：檔案 chunks（以 attachments.file_id 為主，如果未使用 HybridRAG）
        # 如果已使用 HybridRAG，則跳過傳統的向量檢索（避免重複）
        file_ids: List[str] = []
        if attachments:
            file_ids = [a.file_id for a in attachments if a and a.file_id]
            file_ids = self._dedupe_preserve_order(file_ids)

        # 只有在未使用 HybridRAG 或 HybridRAG 未返回結果時，才執行傳統向量檢索
        if not self._use_hybrid_rag or not hybrid_rag_results:
            try:
                embedding = await self._embedding_service.generate_embedding(
                    normalized_query,
                    user_id=user_id,
                    file_id=(file_ids[0] if file_ids else None),
                    task_id=task_id,
                )

                async def _query_one(fid: str) -> List[Dict[str, Any]]:
                    # 修改時間：2026-01-02 - 如果提供了 user 對象，使用帶 ACL 權限檢查的查詢
                    if user is not None:
                        return await asyncio.to_thread(
                            self._vector_store_service.query_vectors_with_acl,
                            user=user,
                            query_embedding=embedding,
                            file_id=fid,
                            user_id=user_id,
                            n_results=self._rag_top_k,
                        )
                    else:
                        # 向後兼容：沒有 user 對象時使用原有方法
                        return await asyncio.to_thread(
                            self._vector_store_service.query_vectors,
                            query_embedding=embedding,
                            file_id=fid,
                            user_id=user_id,
                            n_results=self._rag_top_k,
                        )

                if file_ids:
                    batches = await asyncio.gather(*[_query_one(fid) for fid in file_ids])
                    flat: List[Dict[str, Any]] = []
                    for b in batches:
                        if isinstance(b, list):
                            flat.extend(b)

                    # sort by distance asc
                    flat.sort(key=lambda x: (x.get("distance") is None, x.get("distance", 1e9)))
                    for item in flat[: self._rag_top_k]:
                        meta = item.get("metadata", {}) or {}
                        rag_results.append(
                            {
                                "content": item.get("document", ""),
                                "metadata": {
                                    "file_id": meta.get("file_id"),
                                    "chunk_index": meta.get("chunk_index"),
                                },
                                "distance": item.get("distance"),
                            }
                        )

                else:
                    # 無 attachments 時：僅在 user_based collection 才嘗試 user scope RAG
                    if (
                        getattr(self._vector_store_service, "collection_naming", None)
                        == "user_based"
                    ):
                        # 修改時間：2026-01-02 - 如果提供了 user 對象，使用帶 ACL 權限檢查的查詢
                        if user is not None:
                            batch = await asyncio.to_thread(
                                self._vector_store_service.query_vectors_with_acl,
                                user=user,
                                query_embedding=embedding,
                                user_id=user_id,
                                n_results=self._rag_top_k,
                            )
                        else:
                            # 向後兼容：沒有 user 對象時使用原有方法
                            batch = await asyncio.to_thread(
                                self._vector_store_service.query_vectors,
                                query_embedding=embedding,
                                user_id=user_id,
                                n_results=self._rag_top_k,
                            )
                        if isinstance(batch, list):
                            batch.sort(
                                key=lambda x: (
                                    x.get("distance") is None,
                                    x.get("distance", 1e9),
                                )
                            )
                            for item in batch[: self._rag_top_k]:
                                meta = item.get("metadata", {}) or {}
                                rag_results.append(
                                    {
                                        "content": item.get("document", ""),
                                        "metadata": {
                                            "file_id": meta.get("file_id"),
                                            "chunk_index": meta.get("chunk_index"),
                                        },
                                        "distance": item.get("distance"),
                                    }
                                )

                if rag_results:
                    sources.append("rag_file")

            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "chat_memory_rag_failed",
                    error=str(exc),
                    request_id=request_id,
                    user_id=user_id,
                    session_id=session_id,
                    task_id=task_id,
                )
        else:
            # 如果使用了 HybridRAG，將結果添加到 rag_results
            if hybrid_rag_results:
                rag_results.extend(hybrid_rag_results)

        # 2) AAM：對話長期記憶（MVP：ChromaDB text query）
        try:
            aam = self._get_aam_manager()
            if aam is not None:
                from agents.infra.memory.aam.models import MemoryType

                memories = aam.search_memories(
                    normalized_query,
                    memory_type=MemoryType.LONG_TERM,
                    limit=self._aam_top_k,
                    min_relevance=self._min_aam_relevance,
                )

                # metadata user_id filter
                filtered = []
                for m in memories or []:
                    meta = getattr(m, "metadata", {}) or {}
                    if str(meta.get("user_id") or "") != str(user_id):
                        continue
                    filtered.append(m)

                for m in filtered[: self._aam_top_k]:
                    meta = getattr(m, "metadata", {}) or {}
                    aam_results.append(
                        {
                            "content": getattr(m, "content", ""),
                            "metadata": {
                                "session_id": meta.get("session_id"),
                                "task_id": meta.get("task_id"),
                                "user_id": meta.get("user_id"),
                            },
                            "score": getattr(m, "relevance_score", None),
                        }
                    )

                if aam_results:
                    sources.append("aam")

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "chat_memory_aam_failed",
                error=str(exc),
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
            )

        # 分離圖譜檢索結果（從 rag_results 中提取 source="graph" 的結果）
        graph_results: List[Dict[str, Any]] = []
        vector_results: List[Dict[str, Any]] = []
        for result in rag_results:
            meta = result.get("metadata", {}) or {}
            if meta.get("source") == "graph":
                graph_results.append(result)
            else:
                vector_results.append(result)

        injection_text = self._format_injection(
            aam_memories=aam_results,
            rag_chunks=vector_results,  # 只傳入向量檢索結果
            graph_results=graph_results,  # 單獨傳入圖譜檢索結果
        )
        injection_messages = (
            [{"role": "system", "content": injection_text}] if injection_text else []
        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        sources = self._dedupe_preserve_order(sources)
        hit_count = (len(aam_results) if aam_results else 0) + (
            len(rag_results) if rag_results else 0
        )

        return MemoryRetrievalResult(
            injection_messages=injection_messages,
            memory_hit_count=hit_count,
            memory_sources=sources,
            retrieval_latency_ms=elapsed_ms,
        )

    async def write_from_turn(
        self,
        *,
        user_id: str,
        session_id: str,
        task_id: Optional[str],
        request_id: Optional[str],
        user_text: str,
        assistant_text: str,
    ) -> None:
        """MVP：以 turn snippet 寫入 AAM long-term（失敗不阻擋 chat）。"""
        try:
            aam = self._get_aam_manager()
            if aam is None:
                return

            from agents.infra.memory.aam.models import MemoryPriority, MemoryType

            snippet = (
                f"user: {self._clip(user_text, 800)}\n"
                f"assistant: {self._clip(assistant_text, 800)}"
            )

            aam.store_memory(
                content=snippet,
                memory_type=MemoryType.LONG_TERM,
                priority=MemoryPriority.MEDIUM,
                metadata={
                    "user_id": user_id,
                    "session_id": session_id,
                    "task_id": task_id,
                    "request_id": request_id,
                    "source": "chat_product",
                    "kind": "turn_snippet",
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "chat_memory_write_failed",
                error=str(exc),
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
                task_id=task_id,
            )


_chat_memory_service: Optional[ChatMemoryService] = None


def get_chat_memory_service() -> ChatMemoryService:
    global _chat_memory_service
    if _chat_memory_service is None:
        _chat_memory_service = ChatMemoryService()
    return _chat_memory_service


def reset_chat_memory_service() -> None:
    global _chat_memory_service
    _chat_memory_service = None
