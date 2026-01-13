# 代碼功能說明: RAG 服務 - Capability 向量化存儲和檢索（RAG-2）和策略知識檢索（RAG-3）
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""RAG 服務

實現 Capability 的向量化存儲和檢索（RAG-2 Namespace）。
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import structlog

from agents.task_analyzer.models import (
    Capability,
    CapabilityDiscoveryChunk,
    PolicyConstraintChunk,
)
from agents.task_analyzer.rag_chunk_generator import (
    RAGChunkGenerator,
    RAGRetrievalStrategy,
    get_rag_chunk_generator,
    get_rag_retrieval_strategy,
)
from agents.task_analyzer.rag_namespace import (
    RAGNamespace,
    RAGNamespaceManager,
    get_rag_namespace_manager,
)
from database.chromadb import ChromaCollection, ChromaDBClient
from services.api.services.capability_registry_store_service import (
    get_capability_registry_store_service,
)
from services.api.services.embedding_service import get_embedding_service

logger = structlog.get_logger(__name__)


class RAGService:
    """RAG 服務類 - 處理 Capability 的向量化存儲和檢索"""

    def __init__(self, chroma_client: Optional[ChromaDBClient] = None):
        """
        初始化 RAG 服務

        Args:
            chroma_client: ChromaDB 客戶端（可選）
        """
        self._chroma_client = chroma_client or ChromaDBClient()
        self._chunk_generator = get_rag_chunk_generator()
        self._namespace_manager = get_rag_namespace_manager()
        self._embedding_service = get_embedding_service()
        self._capability_registry = get_capability_registry_store_service()

        # 獲取 RAG-2 Namespace 配置
        rag2_config = self._namespace_manager.get_core_namespace()
        self._rag2_collection_name = rag2_config.storage_location

        # 獲取 RAG-3 Namespace 配置
        rag3_config = self._namespace_manager.get_namespace(RAGNamespace.RAG_3_POLICY_CONSTRAINT)
        self._rag3_collection_name = (
            rag3_config.storage_location if rag3_config else "rag_policy_constraint"
        )

    def _get_rag2_collection(self) -> ChromaCollection:
        """
        獲取 RAG-2 Collection

        Returns:
            ChromaCollection 實例
        """
        collection = self._chroma_client.get_or_create_collection(
            name=self._rag2_collection_name,
            metadata={"namespace": RAGNamespace.RAG_2_CAPABILITY_DISCOVERY},
        )
        return ChromaCollection(collection)

    def store_capability(self, capability: Capability) -> bool:
        """
        將 Capability 向量化並存儲到 RAG-2

        Args:
            capability: Capability 對象

        Returns:
            是否成功存儲
        """
        try:
            # 生成 Chunk
            chunk = self._chunk_generator.generate_capability_chunk(capability)

            # 生成 Embedding
            embedding = self._embedding_service.generate_embedding(chunk.content)
            if not embedding or len(embedding) == 0:
                logger.error(
                    "rag_service_embedding_failed",
                    capability_name=capability.name,
                    agent=capability.agent,
                )
                return False

            # 存儲到 ChromaDB
            collection = self._get_rag2_collection()
            collection.add(
                ids=[chunk.chunk_id],
                embeddings=[embedding],
                documents=[chunk.content],
                metadatas=[chunk.metadata],
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
        """
        將所有 Capability 向量化並存儲到 RAG-2

        Returns:
            存儲結果統計
        """
        try:
            # 獲取所有啟用的 Capability
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
        """
        檢索相關的 Capability（RAG-2）

        Args:
            query: 查詢文本
            top_k: 返回數量
            similarity_threshold: 相似度閾值
            agent_filter: Agent 過濾器（可選）

        Returns:
            檢索結果列表（包含 capability 信息和相似度）
        """
        try:
            # 生成查詢 Embedding
            query_embedding = self._embedding_service.generate_embedding(query)
            if not query_embedding or len(query_embedding) == 0:
                logger.error("rag_service_query_embedding_failed", query=query[:100])
                return []

            # 檢索
            collection = self._get_rag2_collection()

            # 構建 where 過濾條件
            where_filter: Optional[Dict[str, Any]] = None
            if agent_filter:
                where_filter = {"agent": agent_filter}

            # 執行檢索
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # 獲取更多結果以便過濾
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            # 處理結果
            retrieved_results: List[Dict[str, Any]] = []

            if results and "ids" in results and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for i, (doc_id, doc, metadata, distance) in enumerate(
                    zip(ids, documents, metadatas, distances)
                ):
                    # 計算相似度（ChromaDB 返回的是距離，需要轉換為相似度）
                    similarity = 1.0 - distance if distance <= 1.0 else 0.0

                    result_item = {
                        "chunk_id": doc_id,
                        "content": doc,
                        "metadata": metadata,
                        "similarity": similarity,
                        "distance": distance,
                    }
                    retrieved_results.append(result_item)

            # 應用防幻覺檢索策略
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

            return filtered_results

        except Exception as exc:
            logger.error(
                "rag_service_retrieve_capabilities_failed",
                query=query[:100],
                error=str(exc),
            )
            return []

    def format_capabilities_for_prompt(self, retrieved_results: List[Dict[str, Any]]) -> str:
        """
        將檢索到的 Capability 格式化為 Prompt 文本

        Args:
            retrieved_results: 檢索結果列表

        Returns:
            格式化後的 Prompt 文本
        """
        if not retrieved_results:
            return "## 可用能力列表\n\n**警告：未找到任何匹配的能力。請確認查詢是否正確，或檢查能力註冊表。**\n"

        formatted_lines = ["## 可用能力列表\n"]
        formatted_lines.append(
            f"**重要：以下能力是從能力註冊表中檢索到的，您只能使用這些能力。**\n"
        )
        formatted_lines.append(f"**禁止：不能發明或使用未在此列表中的能力。**\n\n")

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
        """
        驗證 Capability 是否存在（硬邊界檢查）

        Args:
            capability_name: Capability 名稱
            agent: Agent 名稱
            retrieved_results: 檢索結果列表

        Returns:
            是否存在
        """
        retrieval_strategy = get_rag_retrieval_strategy()
        return retrieval_strategy.validate_capability_exists(
            capability_name, agent, retrieved_results
        )

    def _get_rag3_collection(self) -> ChromaCollection:
        """
        獲取 RAG-3 Collection

        Returns:
            ChromaCollection 實例
        """
        collection = self._chroma_client.get_or_create_collection(
            name=self._rag3_collection_name,
            metadata={"namespace": RAGNamespace.RAG_3_POLICY_CONSTRAINT},
        )
        return ChromaCollection(collection)

    def store_policy_chunk(self, policy_chunk: PolicyConstraintChunk) -> bool:
        """
        將 Policy Chunk 向量化並存儲到 RAG-3

        Args:
            policy_chunk: PolicyConstraintChunk 對象

        Returns:
            是否成功存儲
        """
        try:
            # 生成 Embedding
            embedding = self._embedding_service.generate_embedding(policy_chunk.content)
            if not embedding or len(embedding) == 0:
                logger.error(
                    "rag_service_policy_embedding_failed",
                    chunk_id=policy_chunk.chunk_id,
                )
                return False

            # 存儲到 ChromaDB
            collection = self._get_rag3_collection()
            collection.add(
                ids=[policy_chunk.chunk_id],
                embeddings=[embedding],
                documents=[policy_chunk.content],
                metadatas=[policy_chunk.metadata],
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
        """
        檢索相關的策略知識（RAG-3）

        Args:
            query: 查詢文本
            top_k: 返回數量
            similarity_threshold: 相似度閾值
            policy_type_filter: 策略類型過濾器（可選）

        Returns:
            檢索結果列表（包含策略信息和相似度）
        """
        try:
            # 生成查詢 Embedding
            query_embedding = self._embedding_service.generate_embedding(query)
            if not query_embedding or len(query_embedding) == 0:
                logger.error("rag_service_policy_query_embedding_failed", query=query[:100])
                return []

            # 檢索
            collection = self._get_rag3_collection()

            # 構建 where 過濾條件
            where_filter: Optional[Dict[str, Any]] = None
            if policy_type_filter:
                where_filter = {"policy_type": policy_type_filter}

            # 執行檢索
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # 獲取更多結果以便過濾
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

            # 處理結果
            retrieved_results: List[Dict[str, Any]] = []

            if results and "ids" in results and len(results["ids"]) > 0:
                ids = results["ids"][0]
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for i, (doc_id, doc, metadata, distance) in enumerate(
                    zip(ids, documents, metadatas, distances)
                ):
                    # 計算相似度（ChromaDB 返回的是距離，需要轉換為相似度）
                    similarity = 1.0 - distance if distance <= 1.0 else 0.0

                    result_item = {
                        "chunk_id": doc_id,
                        "content": doc,
                        "metadata": metadata,
                        "similarity": similarity,
                        "distance": distance,
                    }
                    retrieved_results.append(result_item)

            # 應用防幻覺檢索策略
            retrieval_strategy = get_rag_retrieval_strategy(
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                require_active=False,  # Policy 不需要 is_active 檢查
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

            return filtered_results

        except Exception as exc:
            logger.error(
                "rag_service_retrieve_policies_failed",
                query=query[:100],
                error=str(exc),
            )
            return []

    def format_policies_for_prompt(self, retrieved_results: List[Dict[str, Any]]) -> str:
        """
        將檢索到的策略知識格式化為 Prompt 文本

        Args:
            retrieved_results: 檢索結果列表

        Returns:
            格式化後的 Prompt 文本
        """
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


def get_rag_service(chroma_client: Optional[ChromaDBClient] = None) -> RAGService:
    """
    獲取 RAG Service 實例（單例模式）

    Args:
        chroma_client: ChromaDB 客戶端（可選）

    Returns:
        RAG Service 實例
    """
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = RAGService(chroma_client)
    return _rag_service_instance


# 全局單例實例
_rag_service_instance: Optional[RAGService] = None
