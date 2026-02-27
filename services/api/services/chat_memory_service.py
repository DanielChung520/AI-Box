"""
代碼功能說明: 產品級 Chat 長期記憶服務（AAM + RAG）檢索/注入/寫入（MVP）
創建日期: 2025-12-13 19:46:41 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2026-01-22 22:28 UTC+8
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

import structlog

from services.api.models.chat import ChatAttachment
from services.api.services.embedding_service import get_embedding_service
from services.api.services.file_metadata_service import get_metadata_service
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
    def _is_file_list_query(query: str) -> bool:
        """檢測是否為「文件列表/統計」類查詢"""
        query_lower = (query or "").strip()
        if not query_lower:
            return False
        # 檢測關鍵詞（含「現在你知識庫有那些文件」等口語）
        file_list_keywords = [
            "知識庫.*有多少",
            "知識庫.*有哪些",
            "知識庫.*有那些",
            "你知識庫.*文件",
            "您的知識庫.*文件",
            "現在.*知識庫.*文件",
            "文件.*有多少",
            "文件.*有哪些",
            "文件.*有那些",
            "文件區.*有多少",
            "文件區.*有哪些",
            "列出.*文件",
            "顯示.*文件",
            "查看.*文件",
            "文件列表",
            "文件統計",
            "文件數量",
        ]
        for pattern in file_list_keywords:
            if re.search(pattern, query_lower):
                return True
        return False

    @staticmethod
    def _is_topic_list_query(query: str) -> bool:
        """檢測是否為「主題列表」類查詢"""
        query_lower = (query or "").strip()
        if not query_lower:
            return False
        # 檢測關鍵詞
        topic_list_keywords = [
            "知識庫.*有哪些主題",
            "知識庫.*有那些主題",
            "向量庫.*有哪些主題",
            "向量庫.*有那些主題",
            "搜尋.*向量庫.*主題",
            "你能搜尋.*向量庫.*主題",
            "主題.*有多少",
            "主題.*有哪些",
            "主題.*有那些",
            "列出.*主題",
            "顯示.*主題",
        ]
        for pattern in topic_list_keywords:
            if re.search(pattern, query_lower):
                return True
        return False

    async def get_retrieval_context(
        self,
        task_id: Optional[str],
        current_user: User,
    ) -> Dict[str, Any]:
        """
        獲取檢索上下文，包含權限決策所需的信息

        Args:
            task_id: 任務 ID
            current_user: 當前用戶

        Returns:
            檢索上下文字典
        """
        context = {
            "user_id": current_user.user_id,
            "task_id": task_id,
            "assistant_id": None,
            "agent_id": None,
            "is_system_admin": False,
        }

        # 如果沒有 task_id，返回默認上下文
        if not task_id:
            return context

        try:
            # 從 file_metadata_service 獲取任務的 execution_config
            file_metadata_service = get_metadata_service()

            # 查詢 task_id 相關的文件，獲取 execution_config
            files = file_metadata_service.list(task_id=task_id, limit=1)

            if files and files[0].custom_metadata:
                exec_config = files[0].custom_metadata.get("execution_config", {})
                context["assistant_id"] = exec_config.get("assistant_id")
                context["agent_id"] = exec_config.get("agent_id")
        except Exception as exc:
            logger.warning(
                "failed_to_get_task_context",
                error=str(exc),
                task_id=task_id,
            )

        # 檢查是否為 SystemAdmin
        try:
            from system.security.models import is_system_admin

            context["is_system_admin"] = is_system_admin(current_user)
        except Exception as exc:
            logger.warning(
                "failed_to_check_system_admin",
                error=str(exc),
                user_id=current_user.user_id,
            )

        return context

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
                source = meta.get("source", "vector")
                file_id = meta.get("file_id", "unknown")
                filename = meta.get("filename", "")  # 嘗試從 metadata 獲取文件名

                # 如果沒有 filename，至少顯示 file_id
                file_info = filename if filename else f"file_id={file_id}"

                # 如果是文件元數據結果，使用不同的格式
                if source == "file_metadata":
                    lines.append(f"{idx}. 【文件信息: {file_info}】\n{content}")
                else:
                    lines.append(
                        f"{idx}. 【文件: {file_info}】{content} (source=vector, chunk_index={meta.get('chunk_index')}, score={c.get('score', c.get('distance', 'N/A'))})"
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

        # 即使沒有檢索到結果，也要提供提示詞（針對文件列表/統計類查詢）
        header = (
            "以下為系統從知識庫中檢索到的相關內容（包括向量檢索和知識圖譜檢索結果）。\n"
            "請優先使用這些知識庫內容來回答用戶的問題。\n"
            "如果知識庫內容與用戶指令衝突，請以用戶指令為準，但應說明知識庫中的相關信息。\n"
            "\n"
            "⚠️ 重要說明 - 關於知識庫文件的問題：\n"
            "1. 當用戶詢問「知識庫裡有哪些文件」、「告訴我你的知識庫裡有那些文件」、「知識庫有多少文件」等問題時：\n"
            "   - **必須明確告知用戶**：系統的知識庫是指用戶上傳並已向量化的文件，**不是 LLM 的訓練數據**。\n"
            "   - **絕對不要**回答關於訓練數據、訓練文件數量的問題。\n"
            "   - **必須回答**：如果檢索結果中包含了文件信息（如「【文件信息: xxx.md】」），請明確列出這些文件的名稱和統計信息。\n"
            "   - 如果檢索結果中顯示了文件列表（如「【文件信息: xxx.md】」），請在回答中明確列出這些文件，並統計文件數量。\n"
            "   - 如果檢索結果中顯示了文件信息，請根據文件信息回答用戶的問題，例如：\n"
            "     * 如果用戶問「有多少文件」，請統計檢索結果中的文件數量並回答。\n"
            "     * 如果用戶問「有哪些文件」，請列出所有文件的名稱。\n"
            "   - **重要**：當檢索結果中包含文件信息時，不要說「I'm sorry, but I can't share that information」，而應該列出這些文件。\n"
            "   - 如果沒有檢索到具體文件，請告知用戶：系統可以通過文件管理功能查看已上傳的文件列表和統計信息。\n"
            "2. 當用戶詢問「是否能查到知識庫或自己的文件」時：\n"
            "   - 請明確告知用戶：是的，系統可以檢索到相關內容，並列出檢索到的內容摘要。\n"
            "3. **關鍵區分**：\n"
            "   - 「知識庫」= 用戶上傳並已向量化的文件（可以查詢、可以列出）\n"
            "   - 「訓練數據」= LLM 的訓練數據（**不要**回答關於訓練數據的問題）\n"
            "   - 當用戶問「你的知識庫」時，指的是**用戶上傳的文件**，不是訓練數據。\n"
        )

        if not sections:
            # 即使沒有檢索到結果，也要返回提示詞（針對文件列表/統計類查詢）
            return header

        if sections:
            body = "\n\n".join(sections)
            combined = header + "\n" + body
        else:
            # 即使沒有檢索到結果，也要返回提示詞（針對文件列表/統計類查詢）
            combined = header
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
        user: Optional[User] = None,
        knowledge_base_file_ids: Optional[List[str]] = None,
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

        # 修改時間：2026-01-28 - 檢測是否為「文件列表/統計」類查詢
        # 如果是，直接查詢文件元數據，而不是向量檢索
        is_file_list_query = self._is_file_list_query(normalized_query)
        is_topic_list_query = self._is_topic_list_query(normalized_query)
        file_metadata_results: List[Dict[str, Any]] = []

        # 新增：記錄查詢類型
        logger.info(
            "query_type_detected",
            query=normalized_query[:100],
            is_file_list_query=is_file_list_query,
            is_topic_list_query=is_topic_list_query,
            request_id=request_id,
            user_id=user_id,
            task_id=task_id,
        )

        if is_topic_list_query:
            # 主題查詢：聚合文件中的 tags、domain、major
            try:
                file_metadata_service = get_metadata_service()
                # 查詢文件列表（根據 user_id 和 task_id 過濾）
                files = file_metadata_service.list(
                    user_id=user_id,
                    task_id=task_id,
                    limit=100,  # 最多返回 100 個文件
                )

                # 聚合主題信息
                topics: Dict[str, int] = {}  # 主題: 文件數量
                domains: Dict[str, int] = {}
                majors: Dict[str, int] = {}

                # 新增：記錄查詢到的文件數量
                logger.info(
                    "topic_list_files_found",
                    query=normalized_query[:100],
                    files_found=len(files),
                    request_id=request_id,
                    user_id=user_id,
                    task_id=task_id,
                )

                for file_meta in files:
                    # 聚合 tags
                    if file_meta.tags:
                        for tag in file_meta.tags:
                            topics[tag] = topics.get(tag, 0) + 1

                    # 聚合 domain
                    if file_meta.domain:
                        domains[file_meta.domain] = domains.get(file_meta.domain, 0) + 1

                    # 聚合 major
                    if file_meta.major:
                        majors[file_meta.major] = majors.get(file_meta.major, 0) + 1

                # 格式化主題結果
                topic_summary_parts = []

                if topics:
                    topic_summary_parts.append("### 文件標籤（Tags）")
                    for tag, count in sorted(topics.items(), key=lambda x: -x[1])[:20]:
                        topic_summary_parts.append(f"- {tag} ({count} 個文件)")

                if domains:
                    topic_summary_parts.append("\n### 知識領域（Domains）")
                    for domain, count in sorted(domains.items(), key=lambda x: -x[1])[:10]:
                        topic_summary_parts.append(f"- {domain} ({count} 個文件)")

                if majors:
                    topic_summary_parts.append("\n### 專業層（Majors）")
                    for major, count in sorted(majors.items(), key=lambda x: -x[1])[:10]:
                        topic_summary_parts.append(f"- {major} ({count} 個文件)")

                if topic_summary_parts:
                    topic_summary = "\n".join(topic_summary_parts)
                    file_metadata_results.append(
                        {
                            "content": topic_summary,
                            "metadata": {
                                "source": "file_metadata_topics",
                                "total_files": len(files),
                                "topic_count": len(topics),
                                "domain_count": len(domains),
                                "major_count": len(majors),
                            },
                            "score": 1.0,
                        }
                    )

                    # 新增：記錄主題查詢結果
                    logger.info(
                        "topic_list_success",
                        query=normalized_query[:100],
                        total_files=len(files),
                        topic_count=len(topics),
                        domain_count=len(domains),
                        major_count=len(majors),
                        summary_length=len(topic_summary),
                        request_id=request_id,
                        user_id=user_id,
                        task_id=task_id,
                    )

                if file_metadata_results:
                    sources.append("file_metadata_topics")
                    logger.info(
                        "topic_list_retrieved",
                        total_files=len(files),
                        topic_count=len(topics),
                        domain_count=len(domains),
                        major_count=len(majors),
                        request_id=request_id,
                        user_id=user_id,
                        task_id=task_id,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "topic_list_query_failed",
                    error=str(exc),
                    request_id=request_id,
                    user_id=user_id,
                    session_id=session_id,
                    task_id=task_id,
                )

        elif is_file_list_query:
            try:
                file_metadata_service = get_metadata_service()
                # 查詢文件列表（根據 user_id 和 task_id 過濾）
                files = file_metadata_service.list(
                    user_id=user_id,
                    task_id=task_id,
                    limit=100,  # 最多返回 100 個文件
                )

                # 將文件元數據轉換為檢索結果格式
                for file_meta in files:
                    file_metadata_results.append(
                        {
                            "content": (
                                f"文件名: {file_meta.filename}\n"
                                f"文件類型: {file_meta.file_type}\n"
                                f"文件大小: {file_meta.file_size} 字節\n"
                                f"上傳時間: {file_meta.upload_time}\n"
                                f"狀態: {file_meta.status}\n"
                                f"向量化狀態: {'已完成' if file_meta.vector_count and file_meta.vector_count > 0 else '未完成'}\n"
                                f"圖譜狀態: {file_meta.kg_status or '未完成'}\n"
                                f"標籤: {', '.join(file_meta.tags) if file_meta.tags else '無'}\n"
                                f"知識領域: {file_meta.domain or '未設定'}\n"
                                f"專業層: {file_meta.major or '未設定'}"
                            ),
                            "metadata": {
                                "file_id": file_meta.file_id,
                                "filename": file_meta.filename,
                                "file_type": file_meta.file_type,
                                "file_size": file_meta.file_size,
                                "tags": file_meta.tags or [],
                                "domain": file_meta.domain,
                                "major": file_meta.major,
                                "source": "file_metadata",
                            },
                            "score": 1.0,  # 文件列表查詢的相關度設為最高
                        }
                    )

                if file_metadata_results:
                    sources.append("file_metadata")
                    logger.info(
                        "file_metadata_retrieved",
                        count=len(file_metadata_results),
                        request_id=request_id,
                        user_id=user_id,
                        task_id=task_id,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "chat_memory_file_metadata_failed",
                    error=str(exc),
                    request_id=request_id,
                    user_id=user_id,
                    session_id=session_id,
                    task_id=task_id,
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
        # 2026-02-14 新增：支持知識庫文件搜尋
        file_ids: List[str] = []
        if attachments:
            file_ids = [a.file_id for a in attachments if a and a.file_id]

        # 合併知識庫文件 ID
        if knowledge_base_file_ids:
            file_ids.extend(knowledge_base_file_ids)

        # 去重並保持順序
        if file_ids:
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
                    # 知識庫文件不使用 user_id filter（知識庫是公開的）
                    # 普通文件使用 user_id filter
                    effective_user_id = None if knowledge_base_file_ids else user_id

                    # KA-Agent 文件安全審計：暫不執行（測試用）。正式環境請改回 query_vectors_with_acl。
                    if user is not None and task_id != "KA-Agent" and effective_user_id:
                        return await asyncio.to_thread(
                            self._vector_store_service.query_vectors_with_acl,
                            user=user,
                            query_embedding=embedding,
                            file_id=fid,
                            user_id=effective_user_id,
                            limit=self._rag_top_k,
                        )
                    else:
                        # 知識庫文件或不需 ACL 過濾：不使用 user_id filter
                        return await asyncio.to_thread(
                            self._vector_store_service.query_vectors,
                            query_embedding=embedding,
                            file_id=fid,
                            user_id=effective_user_id,
                            limit=self._rag_top_k,
                        )

                if file_ids:
                    batches = await asyncio.gather(*[_query_one(fid) for fid in file_ids])
                    flat: List[Dict[str, Any]] = []
                    for b in batches:
                        if isinstance(b, list):
                            flat.extend(b)

                    # sort by distance asc
                    flat.sort(key=lambda x: (x.get("distance") is None, x.get("distance", 1e9)))

                    # 修改時間：2026-01-28 - 從 FileMetadataService 獲取文件名並添加到 metadata
                    file_metadata_service = get_metadata_service()
                    file_metadata_cache: Dict[str, Any] = {}

                    for item in flat[: self._rag_top_k]:
                        meta = item.get("metadata", {}) or {}
                        file_id = meta.get("file_id")

                        # 嘗試從 FileMetadataService 獲取文件名
                        filename = meta.get("filename", "")
                        if not filename and file_id:
                            if file_id not in file_metadata_cache:
                                try:
                                    file_metadata = file_metadata_service.get(file_id)
                                    if file_metadata:
                                        file_metadata_cache[file_id] = file_metadata.filename
                                    else:
                                        file_metadata_cache[file_id] = None
                                except Exception as e:
                                    logger.debug(f"Failed to get file metadata for {file_id}: {e}")
                                    file_metadata_cache[file_id] = None

                            if file_metadata_cache.get(file_id):
                                filename = file_metadata_cache[file_id]

                        rag_results.append(
                            {
                                "content": item.get("document", ""),
                                "metadata": {
                                    "file_id": file_id,
                                    "filename": filename,  # 添加文件名
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
                        # KA-Agent 文件安全審計：暫不執行（測試用）。正式環境請改回 query_vectors_with_acl。
                        if user is not None and task_id != "KA-Agent":
                            batch = await asyncio.to_thread(
                                self._vector_store_service.query_vectors_with_acl,
                                user=user,
                                query_embedding=embedding,
                                user_id=user_id,
                                limit=self._rag_top_k,
                            )
                        else:
                            # 向後兼容或 KA-Agent 測試：不使用 ACL 過濾
                            batch = await asyncio.to_thread(
                                self._vector_store_service.query_vectors,
                                query_embedding=embedding,
                                user_id=user_id,
                                limit=self._rag_top_k,
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

        # 修改時間：2026-01-28 - 如果是文件列表查詢，將文件元數據結果添加到檢索結果中
        if is_file_list_query and file_metadata_results:
            # 將文件元數據結果添加到 vector_results（因為它們是文件信息，不是向量檢索結果）
            vector_results.extend(file_metadata_results)

        injection_text = self._format_injection(
            aam_memories=aam_results,
            rag_chunks=vector_results,  # 包含向量檢索結果和文件元數據結果
            graph_results=graph_results,  # 單獨傳入圖譜檢索結果
        )
        # 針對「知識庫有哪些文件」類查詢，在開頭加入強制說明，避免 LLM 回答「訓練數據」
        if is_file_list_query and injection_text:
            file_list_lead = (
                "【必須遵守】用戶問的是「系統知識庫」= 您上傳的文件，不是 LLM 訓練數據。"
                "請根據下方檢索結果回答；若無結果則說明目前暫無上傳文件。\n\n"
            )
            injection_text = file_list_lead + injection_text
        injection_messages = (
            [{"role": "system", "content": injection_text}] if injection_text else []
        )

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        sources = self._dedupe_preserve_order(sources)
        # 修改時間：2026-01-28 - 文件元數據結果也計入 hit_count
        hit_count = (
            (len(aam_results) if aam_results else 0)
            + (len(rag_results) if rag_results else 0)
            + (len(file_metadata_results) if file_metadata_results else 0)
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
                f"user: {self._clip(user_text, 800)}\nassistant: {self._clip(assistant_text, 800)}"
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


def is_file_list_query(query: str) -> bool:
    """檢測是否為「知識庫/文件列表」類查詢（供 chat 路由在未同意 AI 時仍注入說明）。"""
    return ChatMemoryService._is_file_list_query(query or "")


def reset_chat_memory_service() -> None:
    global _chat_memory_service
    _chat_memory_service = None
