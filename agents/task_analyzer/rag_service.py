# 代碼功能說明: RAG 服務 - Capability 向量化存儲和檢索（RAG-2）和策略知識檢索（RAG-3）
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-20
#
# 變更記錄:
# 2026-01-20: 從 ChromaDB 遷移到 Qdrant（統一 VectorDB）

"""RAG 服務

實現 Capability 的向量化存儲和檢索（RAG-2 Namespace）。
使用 Qdrant 作為向量數據庫存儲後端。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

import structlog
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from qdrant_client.models import Distance, PointStruct, VectorParams

from agents.task_analyzer.models import Capability, PolicyConstraintChunk
from agents.task_analyzer.rag_chunk_generator import (
    get_rag_chunk_generator,
    get_rag_retrieval_strategy,
)
from agents.task_analyzer.rag_namespace import RAGNamespace, get_rag_namespace_manager
from services.api.services.capability_registry_store_service import (
    get_capability_registry_store_service,
)
from services.api.services.embedding_service import get_embedding_service
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service

logger = structlog.get_logger(__name__)


def _sync_generate_embedding(embedding_service, content: str) -> List[float]:
    """同步生成 embedding"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(embedding_service.generate_embedding(content))
    finally:
        loop.close()


class RAGService:
    """RAG 服務類 - 處理 Capability 的向量化存儲和檢索"""

    def __init__(self, qdrant_client: Optional[QdrantClient] = None):
        """
        初始化 RAG 服務

        Args:
            qdrant_client: Qdrant 客戶端（可選）
        """
        self._qdrant_client = qdrant_client or get_qdrant_vector_store_service().client
        self._chunk_generator = get_rag_chunk_generator()
        self._namespace_manager = get_rag_namespace_manager()
        self._embedding_service = get_embedding_service()
        self._capability_registry = get_capability_registry_store_service()

        rag2_config = self._namespace_manager.get_core_namespace()
        self._rag2_collection_name = rag2_config.storage_location

        rag3_config = self._namespace_manager.get_namespace(RAGNamespace.RAG_3_POLICY_CONSTRAINT)
        self._rag3_collection_name = (
            rag3_config.storage_location if rag3_config else "rag_policy_constraint"
        )

        self._dimension_cache: Dict[str, Optional[int]] = {}

        logger.info(
            "RAGService initialized",
            rag2_collection=self._rag2_collection_name,
            rag3_collection=self._rag3_collection_name,
        )

    def _ensure_collection(self, collection_name: str) -> None:
        """確保 Collection 存在"""
        try:
            self._qdrant_client.get_collection(collection_name)
        except Exception:
            self._qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=768,
                    distance=Distance.COSINE,
                    on_disk=True,
                ),
            )
            self._qdrant_client.create_payload_index(
                collection_name=collection_name,
                field_name="chunk_id",
                field_schema=qmodels.PayloadSchemaType.KEYWORD,
            )

    def _get_vector_size(self) -> int:
        """獲取向量維度"""
        return 768

    def store_capability(self, capability: Capability) -> bool:
        """將 Capability 向量化並存儲到 RAG-2"""
        try:
            chunk = self._chunk_generator.generate_capability_chunk(capability)
            embedding = _sync_generate_embedding(self._embedding_service, chunk.content)

            if not embedding or len(embedding) == 0:
                logger.error(
                    "rag_service_embedding_failed",
                    capability_name=capability.name,
                    agent=capability.agent,
                )
                return False

            self._ensure_collection(self._rag2_collection_name)

            metadata = chunk.metadata.copy()
            metadata["agent"] = capability.agent
            metadata["capability_name"] = capability.name

            self._qdrant_client.upsert(
                collection_name=self._rag2_collection_name,
                points=[
                    PointStruct(
                        id=chunk.chunk_id,
                        vector=embedding,
                        payload={
                            "chunk_id": chunk.chunk_id,
                            "content": chunk.content,
                            "metadata": json.dumps(metadata, ensure_ascii=False),
                        },
                    )
                ],
            )

            logger.info(
                "rag_service_capability_stored",
                capability_name=capability.name,
                agent=capability.agent,
                chunk_id=chunk.chunk_id,
            )
            return True

        except Exception as exc:
            logger.error(
                "rag_service_store_capability_failed",
                capability_name=capability.name,
                agent=capability.agent,
                error=str(exc),
            )
            return False

    def store_all_capabilities(self) -> Dict[str, Any]:
        """將所有 Capability 向量化並存儲到 RAG-2"""
        try:
            capabilities = self._capability_registry.list_capabilities(is_active=True)

            success_count = 0
            failed_count = 0

            for capability in capabilities:
                if self.store_capability(capability):
                    success_count += 1
                else:
                    failed_count += 1

            result = {
                "total": len(capabilities),
                "success": success_count,
                "failed": failed_count,
            }

            logger.info(
                "rag_service_store_all_capabilities_completed",
                **result,
            )
            return result

        except Exception as exc:
            logger.error(
                "rag_service_store_all_capabilities_failed",
                error=str(exc),
            )
            return {"total": 0, "success": 0, "failed": 0, "error": str(exc)}

    def retrieve_capabilities(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        agent_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """檢索相關的 Capability（RAG-2）"""
        try:
            query_embedding = _sync_generate_embedding(self._embedding_service, query)
            if not query_embedding or len(query_embedding) == 0:
                logger.error("rag_service_query_embedding_failed", query=query[:100])
                return []

            must_conditions = []
            if agent_filter:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="agent",
                        match=qmodels.MatchValue(value=agent_filter),
                    )
                )

            filter_model = None
            if must_conditions:
                filter_model = qmodels.Filter(must=must_conditions)

            try:
                results = self._qdrant_client.query_points(
                    collection_name=self._rag2_collection_name,
                    query=query_embedding,
                    limit=top_k * 2,
                    query_filter=filter_model,
                    with_payload=True,
                ).points
            except Exception:
                return []

            retrieved_results: List[Dict[str, Any]] = []

            for point in results:
                payload = point.payload
                metadata = json.loads(payload.get("metadata", "{}"))
                similarity = point.score

                if similarity >= similarity_threshold:
                    result_item = {
                        "chunk_id": payload.get("chunk_id"),
                        "content": payload.get("content"),
                        "metadata": metadata,
                        "similarity": similarity,
                    }
                    retrieved_results.append(result_item)

            retrieval_strategy = get_rag_retrieval_strategy(
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                require_active=True,
            )
            filtered_results = retrieval_strategy.filter_results(
                retrieved_results,
                RAGNamespace.RAG_2_CAPABILITY_DISCOVERY,
            )

            logger.info(
                "rag_service_capabilities_retrieved",
                query=query[:100],
                total_results=len(retrieved_results),
                filtered_results=len(filtered_results),
            )

            return filtered_results[:top_k]

        except Exception as exc:
            logger.error(
                "rag_service_retrieve_capabilities_failed",
                query=query[:100],
                error=str(exc),
            )
            return []

    def format_capabilities_for_prompt(self, retrieved_results: List[Dict[str, Any]]) -> str:
        """將檢索到的 Capability 格式化為 Prompt 文本"""
        if not retrieved_results:
            return "## 可用能力列表\n\n**警告：未找到任何匹配的能力。請確認查詢是否正確，或檢查能力註冊表。**\n"

        formatted_lines = ["## 可用能力列表\n"]
        formatted_lines.append("**重要：以下能力是從能力註冊表中檢索到的，您只能使用這些能力。**\n")
        formatted_lines.append("**禁止：不能發明或使用未在此列表中的能力。**\n\n")

        for i, result in enumerate(retrieved_results, 1):
            metadata = result.get("metadata", {})
            content = result.get("content", "")

            agent = metadata.get("agent", "Unknown")
            capability_name = metadata.get("capability_name", "Unknown")
            input_type = metadata.get("input_type", "Unknown")
            output_type = metadata.get("output_type", "Unknown")
            description = metadata.get("description", "")
            similarity = result.get("similarity", 0.0)

            formatted_lines.append(f"### {i}. {capability_name} (Agent: {agent})")
            formatted_lines.append(f"- **相似度**: {similarity:.2%}")
            formatted_lines.append(f"- **輸入類型**: {input_type}")
            formatted_lines.append(f"- **輸出類型**: {output_type}")
            if description:
                formatted_lines.append(f"- **描述**: {description}")
            formatted_lines.append(f"- **詳細信息**:\n```\n{content}\n```\n")

        return "\n".join(formatted_lines)

    def validate_capability_exists(
        self, capability_name: str, agent: str, retrieved_results: List[Dict[str, Any]]
    ) -> bool:
        """驗證 Capability 是否存在（硬邊界檢查）"""
        retrieval_strategy = get_rag_retrieval_strategy()
        return retrieval_strategy.validate_capability_exists(
            capability_name, agent, retrieved_results
        )

    def store_policy_chunk(self, policy_chunk: PolicyConstraintChunk) -> bool:
        """將 Policy Chunk 向量化並存儲到 RAG-3"""
        try:
            embedding = _sync_generate_embedding(self._embedding_service, policy_chunk.content)
            if not embedding or len(embedding) == 0:
                logger.error(
                    "rag_service_policy_embedding_failed",
                    chunk_id=policy_chunk.chunk_id,
                )
                return False

            self._ensure_collection(self._rag3_collection_name)

            self._qdrant_client.upsert(
                collection_name=self._rag3_collection_name,
                points=[
                    PointStruct(
                        id=policy_chunk.chunk_id,
                        vector=embedding,
                        payload={
                            "chunk_id": policy_chunk.chunk_id,
                            "content": policy_chunk.content,
                            "metadata": json.dumps(policy_chunk.metadata, ensure_ascii=False),
                        },
                    )
                ],
            )

            logger.info(
                "rag_service_policy_chunk_stored",
                chunk_id=policy_chunk.chunk_id,
                policy_type=policy_chunk.metadata.get("policy_type"),
            )
            return True

        except Exception as exc:
            logger.error(
                "rag_service_store_policy_chunk_failed",
                chunk_id=policy_chunk.chunk_id,
                error=str(exc),
            )
            return False

    def retrieve_policies(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        policy_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """檢索相關的策略知識（RAG-3）"""
        try:
            query_embedding = _sync_generate_embedding(self._embedding_service, query)
            if not query_embedding or len(query_embedding) == 0:
                logger.error("rag_service_policy_query_embedding_failed", query=query[:100])
                return []

            must_conditions = []
            if policy_type_filter:
                must_conditions.append(
                    qmodels.FieldCondition(
                        key="policy_type",
                        match=qmodels.MatchValue(value=policy_type_filter),
                    )
                )

            filter_model = None
            if must_conditions:
                filter_model = qmodels.Filter(must=must_conditions)

            try:
                results = self._qdrant_client.query_points(
                    collection_name=self._rag3_collection_name,
                    query=query_embedding,
                    limit=top_k * 2,
                    query_filter=filter_model,
                    with_payload=True,
                ).points
            except Exception:
                return []

            retrieved_results: List[Dict[str, Any]] = []

            for point in results:
                payload = point.payload
                metadata = json.loads(payload.get("metadata", "{}"))
                similarity = point.score

                if similarity >= similarity_threshold:
                    result_item = {
                        "chunk_id": payload.get("chunk_id"),
                        "content": payload.get("content"),
                        "metadata": metadata,
                        "similarity": similarity,
                    }
                    retrieved_results.append(result_item)

            retrieval_strategy = get_rag_retrieval_strategy(
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                require_active=False,
            )
            filtered_results = retrieval_strategy.filter_results(
                retrieved_results,
                RAGNamespace.RAG_3_POLICY_CONSTRAINT,
            )

            logger.info(
                "rag_service_policies_retrieved",
                query=query[:100],
                total_results=len(retrieved_results),
                filtered_results=len(filtered_results),
            )

            return filtered_results[:top_k]

        except Exception as exc:
            logger.error(
                "rag_service_retrieve_policies_failed",
                query=query[:100],
                error=str(exc),
            )
            return []

    def format_policies_for_prompt(self, retrieved_results: List[Dict[str, Any]]) -> str:
        """將檢索到的策略知識格式化為 Prompt 文本"""
        if not retrieved_results:
            return "## 策略知識\n\n**未找到相關的策略知識。**\n"

        formatted_lines = ["## 策略知識\n"]
        formatted_lines.append("**以下策略知識可能與當前任務相關：**\n\n")

        for i, result in enumerate(retrieved_results, 1):
            metadata = result.get("metadata", {})
            content = result.get("content", "")

            policy_type = metadata.get("policy_type", "Unknown")
            risk_level = metadata.get("risk_level", "low")
            scope = metadata.get("scope", "all_agents")
            similarity = result.get("similarity", 0.0)

            formatted_lines.append(f"### {i}. 策略類型: {policy_type}")
            formatted_lines.append(f"- **風險等級**: {risk_level}")
            formatted_lines.append(f"- **適用範圍**: {scope}")
            formatted_lines.append(f"- **相似度**: {similarity:.2%}")
            formatted_lines.append(f"- **詳細信息**:\n```\n{content}\n```\n")

        return "\n".join(formatted_lines)


def get_rag_service(qdrant_client: Optional[QdrantClient] = None) -> RAGService:
    """
    獲取 RAG Service 實例（單例模式）

    Args:
        qdrant_client: Qdrant 客戶端（可選）

    Returns:
        RAG Service 實例
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService(qdrant_client)
    return _rag_service_instance


_rag_service_instance: Optional[RAGService] = None
