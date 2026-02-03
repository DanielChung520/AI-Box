# 代碼功能說明: 向量存儲服務（Qdrant）
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""向量存儲服務 - 使用 Qdrant 存儲決策語義向量（符合 GRO 規範）"""

import logging
from typing import Any, Dict, List, Optional, Union

from agents.task_analyzer.models import DecisionLog, GroDecisionLog

logger = logging.getLogger(__name__)

# 固定的 file_id 用於 routing memory（全局 collection）
ROUTING_MEMORY_FILE_ID = "routing_memory"


class RoutingVectorStore:
    """Routing Memory 向量存儲類"""

    def __init__(self):
        """初始化向量存儲"""
        self._vector_store_service = None
        self._embedding_service = None

    def _get_vector_store_service(self):
        """獲取向量存儲服務（懶加載，使用 Qdrant）"""
        if self._vector_store_service is None:
            try:
                from services.api.services.qdrant_vector_store_service import (
                    get_qdrant_vector_store_service,
                )

                self._vector_store_service = get_qdrant_vector_store_service()
            except Exception as e:
                logger.warning(f"Failed to initialize Vector Store Service: {e}")
                self._vector_store_service = None
        return self._vector_store_service

    def _get_embedding_service(self):
        """獲取 Embedding 服務（懶加載）"""
        if self._embedding_service is None:
            try:
                from services.api.services.embedding_service import get_embedding_service

                self._embedding_service = get_embedding_service()
            except Exception as e:
                logger.warning(f"Failed to initialize Embedding Service: {e}")
                self._embedding_service = None
        return self._embedding_service

    async def add(self, semantic: str, decision_log: Union[DecisionLog, GroDecisionLog]) -> bool:
        """
        添加決策語義到向量存儲（符合 GRO 規範）

        Args:
            semantic: 決策語義文本
            decision_log: 決策日誌對象（GroDecisionLog 或 DecisionLog）

        Returns:
            是否成功
        """
        try:
            vector_service = self._get_vector_store_service()
            embedding_service = self._get_embedding_service()

            if vector_service is None or embedding_service is None:
                logger.warning("Vector store or embedding service not available")
                return False

            # 生成 embedding（使用 Qdrant API）
            embedding = await embedding_service.generate_embedding(text=semantic)

            # 準備 metadata（符合 GRO 規範）
            if isinstance(decision_log, GroDecisionLog):
                # GRO 規範格式
                metadata = {
                    "react_id": decision_log.react_id,
                    "iteration": decision_log.iteration,
                    "state": decision_log.state.value,
                    "outcome": decision_log.outcome.value,
                    "action": decision_log.decision.action.value,
                    "next_state": decision_log.decision.next_state.value,
                }
                # 從 input_signature 提取信息
                input_sig = decision_log.input_signature
                if input_sig:
                    metadata["intent_type"] = input_sig.get("intent_type", "")
                    metadata["complexity"] = input_sig.get("complexity", "")
                    metadata["risk_level"] = input_sig.get("risk_level", "")
                # 從 metadata 提取 chosen_path 信息
                if decision_log.metadata:
                    metadata["chosen_agent"] = decision_log.metadata.get("chosen_agent", "")
                    metadata["chosen_model"] = decision_log.metadata.get("chosen_model", "")
                    chosen_tools = decision_log.metadata.get("chosen_tools", [])
                    if chosen_tools:
                        metadata["chosen_tools"] = (
                            ",".join(chosen_tools)
                            if isinstance(chosen_tools, list)
                            else str(chosen_tools)
                        )
                    metadata["success"] = decision_log.outcome.value == "success"
            else:
                # 舊版 DecisionLog 格式（向後兼容）
                metadata = {
                    "decision_id": decision_log.decision_id,
                    "intent_type": decision_log.router_output.intent_type,
                    "complexity": decision_log.router_output.complexity,
                    "risk_level": decision_log.router_output.risk_level,
                    "chosen_agent": decision_log.decision_engine.chosen_agent or "",
                    "chosen_model": decision_log.decision_engine.chosen_model or "",
                    "chosen_tools": (
                        ",".join(decision_log.decision_engine.chosen_tools)
                        if decision_log.decision_engine.chosen_tools
                        else ""
                    ),
                    "success": (
                        decision_log.execution_result.get("success", False)
                        if decision_log.execution_result
                        else False
                    ),
                }

            # Qdrant 會自動創建 collection，不需要顯式調用

            # 準備 chunks 和 embeddings（使用 store_vectors API）
            chunks = [
                {
                    "text": semantic,
                    "metadata": metadata,
                    "chunk_index": 0,
                }
            ]

            # 存儲向量
            vector_service.store_vectors(
                file_id=ROUTING_MEMORY_FILE_ID,
                chunks=chunks,
                embeddings=[embedding],
                user_id=None,
            )

            if isinstance(decision_log, GroDecisionLog):
                logger.info(
                    f"Stored routing memory vector: react_id={decision_log.react_id}, "
                    f"iteration={decision_log.iteration}, state={decision_log.state.value}"
                )
            else:
                logger.info(f"Stored routing memory vector: decision_id={decision_log.decision_id}")

            return True

        except Exception as e:
            logger.error(f"Failed to add routing memory vector: {e}", exc_info=True)
            return False

    async def search(
        self, query: str, top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相似決策（符合 GRO 規範）

        Args:
            query: 查詢文本
            top_k: 返回前 K 個結果
            filters: 過濾條件（如 success=True, outcome="success", state="DECISION"）

        Returns:
            相似決策列表，每個結果包含 decision_id 或 (react_id, iteration)、metadata、distance
        """
        try:
            vector_service = self._get_vector_store_service()
            embedding_service = self._get_embedding_service()

            if vector_service is None or embedding_service is None:
                logger.warning("Vector store or embedding service not available")
                return []

            # 生成查詢 embedding（使用 Qdrant API）
            query_embedding = await embedding_service.generate_embedding(text=query)

            # 構建 where 過濾條件（Qdrant 格式，已从 ChromaDB 迁移）
            where_clause = None
            if filters:
                where_clause = {}
                # 支持 GRO 規範字段
                if "outcome" in filters:
                    where_clause["outcome"] = filters["outcome"]
                if "state" in filters:
                    where_clause["state"] = filters["state"]
                if "react_id" in filters:
                    where_clause["react_id"] = filters["react_id"]
                # 向後兼容字段
                if "success" in filters:
                    where_clause["success"] = filters["success"]
                if "intent_type" in filters:
                    where_clause["intent_type"] = filters["intent_type"]
                if "complexity" in filters:
                    where_clause["complexity"] = filters["complexity"]
                if "risk_level" in filters:
                    where_clause["risk_level"] = filters["risk_level"]
                if not where_clause:
                    where_clause = None

            # 查詢相似向量（使用 Qdrant API）
            results = vector_service.query_vectors(
                query_embedding=query_embedding,
                file_id=ROUTING_MEMORY_FILE_ID,
                user_id=None,
                limit=top_k,
            )

            # 轉換結果格式（兼容 Qdrant 的 payload）
            similar_decisions: List[Dict[str, Any]] = []
            for result in results:
                # Qdrant 使用 payload（已从 ChromaDB 迁移）
                metadata = result.get("payload", result.get("metadata", {}))
                # 構建 decision_id 或 react_id + iteration
                if "react_id" in metadata and "iteration" in metadata:
                    decision_id = f"{metadata['react_id']}_{metadata['iteration']}"
                else:
                    decision_id = metadata.get("decision_id", "")

                similar_decisions.append(
                    {
                        "decision_id": decision_id,
                        "react_id": metadata.get("react_id"),
                        "iteration": metadata.get("iteration"),
                        "distance": 1.0 - result.get("score", 0.0)
                        if "score" in result
                        else result.get("distance", 0.0),
                        "metadata": metadata,
                        "document": result.get("document", ""),
                    }
                )

            logger.info(
                f"Found {len(similar_decisions)} similar decisions for query: {query[:50]}..."
            )
            return similar_decisions

        except Exception as e:
            logger.error(f"Failed to search routing memory: {e}", exc_info=True)
            return []
