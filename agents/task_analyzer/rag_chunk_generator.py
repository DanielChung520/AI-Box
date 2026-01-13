# 代碼功能說明: RAG Chunk 生成器
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""RAG Chunk 生成器

實現 Chunk 生成邏輯和防幻覺檢索策略。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import structlog

from agents.task_analyzer.models import (
    ArchitectureAwarenessChunk,
    Capability,
    CapabilityDiscoveryChunk,
    PolicyConstraintChunk,
)
from agents.task_analyzer.rag_namespace import RAGNamespace

logger = structlog.get_logger(__name__)


class RAGChunkGenerator:
    """RAG Chunk 生成器類"""

    @staticmethod
    def generate_capability_chunk(capability: Capability) -> CapabilityDiscoveryChunk:
        """
        從 Capability 生成 Chunk（RAG-2，最重要）

        Args:
            capability: Capability 對象

        Returns:
            CapabilityDiscoveryChunk
        """
        # 構建結構化內容
        content = f"""Agent: {capability.agent}
Capability: {capability.name}
Input: {capability.input}
Output: {capability.output}
Constraints: {json.dumps(capability.constraints, ensure_ascii=False)}
Description: {capability.description or 'N/A'}
Version: {capability.version}"""

        # 構建元數據
        metadata: Dict[str, Any] = {
            "agent": capability.agent,
            "capability_name": capability.name,
            "input_type": capability.input,
            "output_type": capability.output,
            "constraints": capability.constraints,
            "is_active": capability.is_active,
            "version": capability.version,
            "created_at": datetime.utcnow().isoformat(),
        }

        # 添加額外元數據
        if capability.metadata:
            metadata.update(capability.metadata)

        chunk_id = f"{capability.agent}-{capability.name}-{capability.version}"

        return CapabilityDiscoveryChunk(
            chunk_id=chunk_id,
            namespace=RAGNamespace.RAG_2_CAPABILITY_DISCOVERY,
            content=content,
            metadata=metadata,
            embedding=None,  # 向量嵌入將在存儲時生成
        )

    @staticmethod
    def generate_policy_chunk(
        policy_type: str,
        risk_level: str,
        scope: str,
        conditions: Dict[str, Any],
        description: str,
        policy_id: Optional[str] = None,
    ) -> PolicyConstraintChunk:
        """
        從 Policy 生成 Chunk（RAG-3）

        Args:
            policy_type: 策略類型（forbidden/dangerous/requires_confirmation）
            risk_level: 風險等級（low/mid/high）
            scope: 適用範圍（all_agents/specific_agent）
            conditions: 觸發條件
            description: 策略描述
            policy_id: 策略 ID（可選）

        Returns:
            PolicyConstraintChunk
        """
        # 構建內容
        content = f"""Policy Type: {policy_type}
Risk Level: {risk_level}
Scope: {scope}
Conditions: {json.dumps(conditions, ensure_ascii=False)}
Description: {description}"""

        # 構建元數據
        metadata: Dict[str, Any] = {
            "policy_type": policy_type,
            "risk_level": risk_level,
            "scope": scope,
            "conditions": conditions,
            "created_at": datetime.utcnow().isoformat(),
        }

        chunk_id = policy_id or f"policy-{uuid4().hex[:8]}"

        return PolicyConstraintChunk(
            chunk_id=chunk_id,
            namespace=RAGNamespace.RAG_3_POLICY_CONSTRAINT,
            content=content,
            metadata=metadata,
            embedding=None,  # 向量嵌入將在存儲時生成
        )

    @staticmethod
    def generate_architecture_chunk(
        doc_type: str,
        doc_id: str,
        section: str,
        content_text: str,
        doc_metadata: Optional[Dict[str, Any]] = None,
    ) -> ArchitectureAwarenessChunk:
        """
        從架構文檔生成 Chunk（RAG-1）

        Args:
            doc_type: 文檔類型（system_topology/orchestrator_doc/agent_hierarchy）
            doc_id: 文檔 ID
            section: 章節名稱
            content_text: 文本內容
            doc_metadata: 文檔元數據（可選）

        Returns:
            ArchitectureAwarenessChunk
        """
        # 構建元數據
        metadata: Dict[str, Any] = {
            "doc_type": doc_type,
            "doc_id": doc_id,
            "section": section,
            "created_at": datetime.utcnow().isoformat(),
        }

        # 添加額外元數據
        if doc_metadata:
            metadata.update(doc_metadata)

        chunk_id = f"{doc_id}-{section}-{uuid4().hex[:8]}"

        return ArchitectureAwarenessChunk(
            chunk_id=chunk_id,
            namespace=RAGNamespace.RAG_1_ARCHITECTURE_AWARENESS,
            content=content_text,
            metadata=metadata,
            embedding=None,  # 向量嵌入將在存儲時生成
        )


class RAGRetrievalStrategy:
    """RAG 檢索策略類（防幻覺）"""

    # 默認配置
    DEFAULT_TOP_K = 5
    DEFAULT_SIMILARITY_THRESHOLD = 0.7

    def __init__(
        self,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        require_active: bool = True,
    ):
        """
        初始化檢索策略

        Args:
            top_k: Top-K 限制（默認 5）
            similarity_threshold: 相似度閾值（默認 0.7）
            require_active: 是否只返回啟用的項目（默認 True）
        """
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.require_active = require_active

    def filter_results(
        self,
        results: List[Dict[str, Any]],
        namespace: str,
    ) -> List[Dict[str, Any]]:
        """
        過濾檢索結果（防幻覺）

        Args:
            results: 檢索結果列表
            namespace: Namespace ID

        Returns:
            過濾後的結果列表
        """
        if not results:
            # 硬邊界檢查：檢索結果為空 = 能力不存在
            logger.warning(
                "rag_retrieval_empty_results",
                namespace=namespace,
                message="檢索結果為空，表示能力不存在（硬邊界檢查）",
            )
            return []

        filtered_results = []

        for result in results[: self.top_k]:  # Top-K 限制
            # 相似度閾值檢查
            similarity = result.get("similarity", 0.0)
            if similarity < self.similarity_threshold:
                logger.debug(
                    "rag_retrieval_low_similarity",
                    namespace=namespace,
                    similarity=similarity,
                    threshold=self.similarity_threshold,
                )
                continue

            # 元數據過濾（只返回 is_active=true 的項目）
            if self.require_active and namespace == RAGNamespace.RAG_2_CAPABILITY_DISCOVERY:
                metadata = result.get("metadata", {})
                is_active = metadata.get("is_active", True)
                if not is_active:
                    logger.debug(
                        "rag_retrieval_inactive_capability",
                        namespace=namespace,
                        capability=metadata.get("capability_name"),
                    )
                    continue

            filtered_results.append(result)

        if not filtered_results:
            logger.warning(
                "rag_retrieval_all_filtered",
                namespace=namespace,
                original_count=len(results),
                message="所有結果都被過濾，表示沒有匹配的能力",
            )

        return filtered_results

    def validate_capability_exists(
        self, capability_name: str, agent: str, results: List[Dict[str, Any]]
    ) -> bool:
        """
        驗證 Capability 是否存在（硬邊界檢查）

        Args:
            capability_name: Capability 名稱
            agent: Agent 名稱
            results: 檢索結果列表

        Returns:
            是否存在
        """
        if not results:
            return False

        for result in results:
            metadata = result.get("metadata", {})
            if (
                metadata.get("capability_name") == capability_name
                and metadata.get("agent") == agent
            ):
                return True

        return False


def get_rag_chunk_generator() -> RAGChunkGenerator:
    """
    獲取 RAG Chunk Generator 實例

    Returns:
        RAG Chunk Generator 實例
    """
    return RAGChunkGenerator()


def get_rag_retrieval_strategy(
    top_k: int = RAGRetrievalStrategy.DEFAULT_TOP_K,
    similarity_threshold: float = RAGRetrievalStrategy.DEFAULT_SIMILARITY_THRESHOLD,
    require_active: bool = True,
) -> RAGRetrievalStrategy:
    """
    獲取 RAG Retrieval Strategy 實例

    Args:
        top_k: Top-K 限制
        similarity_threshold: 相似度閾值
        require_active: 是否只返回啟用的項目

    Returns:
        RAG Retrieval Strategy 實例
    """
    return RAGRetrievalStrategy(
        top_k=top_k,
        similarity_threshold=similarity_threshold,
        require_active=require_active,
    )
