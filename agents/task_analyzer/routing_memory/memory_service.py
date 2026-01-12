# 代碼功能說明: Routing Memory 服務
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Routing Memory 服務 - 統一的決策記憶存儲接口"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from agents.task_analyzer.models import DecisionLog, GroDecisionLog
from agents.task_analyzer.routing_memory.metadata_store import RoutingMetadataStore
from agents.task_analyzer.routing_memory.semantic_extractor import build_routing_semantic
from agents.task_analyzer.routing_memory.vector_store import RoutingVectorStore

logger = logging.getLogger(__name__)


class RoutingMemoryService:
    """Routing Memory 服務類"""

    def __init__(self):
        """初始化 Routing Memory 服務"""
        self.vector_store = RoutingVectorStore()
        self.metadata_store = RoutingMetadataStore()

    async def record_decision(
        self,
        decision_log: Union[DecisionLog, GroDecisionLog],
        react_id: Optional[str] = None,
        iteration: Optional[int] = None,
    ) -> bool:
        """
        記錄決策（異步，Fire-and-Forget）

        支持 GRO 規範的 GroDecisionLog 和舊版 DecisionLog（向後兼容）。

        Args:
            decision_log: 決策日誌（GroDecisionLog 或 DecisionLog）
            react_id: ReAct session ID（僅當 decision_log 為舊版 DecisionLog 時需要）
            iteration: 迭代次數（僅當 decision_log 為舊版 DecisionLog 時需要）

        Returns:
            是否成功（注意：這是異步操作，返回值可能不準確）
        """
        try:
            # 如果是舊版 DecisionLog，轉換為 GroDecisionLog
            if isinstance(decision_log, DecisionLog):
                if react_id is None or iteration is None:
                    logger.warning(
                        "Legacy DecisionLog requires react_id and iteration for conversion. "
                        "Generating default values."
                    )
                    import uuid

                    react_id = react_id or str(uuid.uuid4())
                    iteration = iteration or 0
                gro_decision_log = GroDecisionLog.from_legacy_decision_log(
                    decision_log, react_id, iteration
                )
            else:
                gro_decision_log = decision_log

            # 提取語義
            semantic = build_routing_semantic(gro_decision_log)

            # 異步寫入（不阻塞主流程）
            asyncio.create_task(self._write_decision(gro_decision_log, semantic))

            return True

        except Exception as e:
            logger.error(f"Failed to record decision: {e}", exc_info=True)
            return False

    async def _write_decision(self, decision_log: GroDecisionLog, semantic: str) -> None:
        """
        寫入決策（內部方法）

        Args:
            decision_log: GRO 規範的決策日誌
            semantic: 決策語義
        """
        try:
            # 1. 寫入向量存儲（ChromaDB）
            await self.vector_store.add(semantic, decision_log)

            # 2. 寫入元數據存儲（ArangoDB）
            self.metadata_store.save(decision_log)

            logger.info(
                f"Successfully recorded decision: react_id={decision_log.react_id}, "
                f"iteration={decision_log.iteration}, state={decision_log.state.value}"
            )

        except Exception as e:
            # 失敗不影響主流程
            logger.error(f"Failed to write decision: {e}", exc_info=True)

    async def recall_similar_decisions(
        self,
        query: Optional[str] = None,
        routing_key: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        檢索相似決策（符合 GRO 規範，支持向量檢索和 routing_key 查詢）

        Args:
            query: 查詢文本（用於向量相似度搜索）
            routing_key: routing_key 查詢（基於 input_signature 的結構化查詢）
            top_k: 返回前 K 個結果
            filters: 過濾條件（如 success=True, outcome="success", cost < threshold）

        Returns:
            相似決策列表（字典格式，用於 Context Bias）
        """
        try:
            decision_logs: List[Dict[str, Any]] = []

            if routing_key:
                # 使用 routing_key 進行結構化查詢（元數據過濾）
                # routing_key 是 input_signature 的簡化版本
                query_filters = {}
                if "intent_type" in routing_key:
                    query_filters["intent_type"] = routing_key["intent_type"]
                if "complexity" in routing_key:
                    query_filters["complexity"] = routing_key["complexity"]
                if "risk_level" in routing_key:
                    query_filters["risk_level"] = routing_key["risk_level"]
                if "state" in routing_key:
                    query_filters["state"] = routing_key["state"]
                if "outcome" in routing_key:
                    query_filters["outcome"] = routing_key["outcome"]

                # 合併用戶提供的 filters
                if filters:
                    query_filters.update(filters)

                # 從元數據存儲查詢
                metadata_results = self.metadata_store.query(
                    react_id=routing_key.get("react_id"),
                    state=query_filters.get("state"),
                    outcome=query_filters.get("outcome"),
                    intent_type=query_filters.get("intent_type"),
                    complexity=query_filters.get("complexity"),
                    risk_level=query_filters.get("risk_level"),
                    success=query_filters.get("success"),
                    limit=top_k,
                )

                decision_logs = metadata_results

            elif query:
                # 使用向量相似度搜索
                # 1. 向量檢索
                similar_results = await self.vector_store.search(
                    query, top_k=top_k * 2, filters=filters
                )  # 獲取更多結果以便後續過濾

                # 2. 從元數據存儲獲取完整信息
                for result in similar_results:
                    decision_id = result.get("decision_id")
                    react_id = result.get("react_id")
                    iteration = result.get("iteration")

                    metadata = None
                    if react_id is not None and iteration is not None:
                        metadata = self.metadata_store.get(react_id=react_id, iteration=iteration)
                    elif decision_id:
                        metadata = self.metadata_store.get(decision_id=decision_id)

                    if metadata:
                        # 添加相似度距離
                        metadata["similarity_distance"] = result.get("distance", 0.0)
                        decision_logs.append(metadata)

                # 3. 應用過濾條件
                if filters:
                    if filters.get("success") is not None:
                        decision_logs = [
                            d for d in decision_logs if d.get("success") == filters.get("success")
                        ]
                    if filters.get("outcome") is not None:
                        decision_logs = [
                            d for d in decision_logs if d.get("outcome") == filters.get("outcome")
                        ]
                    if filters.get("max_cost") is not None:
                        decision_logs = [
                            d
                            for d in decision_logs
                            if d.get("cost", 0) < filters.get("max_cost", float("inf"))
                        ]

                # 4. 排序（相似度 + 成功率 + 成本）
                decision_logs.sort(
                    key=lambda x: (
                        -x.get("similarity_distance", 1.0),  # 距離越小越好（負號）
                        -x.get("success", False),  # 成功優先
                        x.get("cost", float("inf")),  # 成本越低越好
                    )
                )

                # 5. 限制返回數量
                decision_logs = decision_logs[:top_k]
            else:
                logger.warning("Either query or routing_key must be provided")
                return []

            logger.info(f"Recalled {len(decision_logs)} similar decisions")
            return decision_logs

        except Exception as e:
            logger.error(f"Failed to recall similar decisions: {e}", exc_info=True)
            return []
