# 代碼功能說明: Routing Memory 服務
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""Routing Memory 服務 - 統一的決策記憶存儲接口"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from agents.task_analyzer.models import DecisionLog
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

    async def record_decision(self, decision_log: DecisionLog) -> bool:
        """
        記錄決策（異步，Fire-and-Forget）

        Args:
            decision_log: 決策日誌

        Returns:
            是否成功（注意：這是異步操作，返回值可能不準確）
        """
        try:
            # 提取語義
            semantic = build_routing_semantic(decision_log)

            # 異步寫入（不阻塞主流程）
            asyncio.create_task(self._write_decision(decision_log, semantic))

            return True

        except Exception as e:
            logger.error(f"Failed to record decision: {e}", exc_info=True)
            return False

    async def _write_decision(self, decision_log: DecisionLog, semantic: str) -> None:
        """
        寫入決策（內部方法）

        Args:
            decision_log: 決策日誌
            semantic: 決策語義
        """
        try:
            # 1. 寫入向量存儲（ChromaDB）
            await self.vector_store.add(semantic, decision_log)

            # 2. 寫入元數據存儲（ArangoDB）
            self.metadata_store.save(decision_log)

            logger.info(f"Successfully recorded decision: {decision_log.decision_id}")

        except Exception as e:
            # 失敗不影響主流程
            logger.error(f"Failed to write decision: {e}", exc_info=True)

    async def recall_similar_decisions(
        self, query: str, top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        檢索相似決策

        Args:
            query: 查詢文本
            top_k: 返回前 K 個結果
            filters: 過濾條件（如 success=True, cost < threshold）

        Returns:
            相似決策列表（字典格式，用於 Context Bias）
        """
        try:
            # 1. 向量檢索
            similar_results = await self.vector_store.search(query, top_k=top_k, filters=filters)

            # 2. 從元數據存儲獲取完整信息
            decision_logs: List[Dict[str, Any]] = []
            for result in similar_results:
                decision_id = result.get("decision_id")
                if decision_id:
                    metadata = self.metadata_store.get(decision_id)
                    if metadata:
                        # 返回字典格式（用於 Context Bias）
                        decision_logs.append(metadata)

            # 3. 應用過濾條件
            if filters:
                if filters.get("success") is not None:
                    decision_logs = [
                        d for d in decision_logs if d.get("success") == filters.get("success")
                    ]
                if filters.get("max_cost") is not None:
                    decision_logs = [
                        d
                        for d in decision_logs
                        if d.get("cost", 0) < filters.get("max_cost", float("inf"))
                    ]

            logger.info(f"Recalled {len(decision_logs)} similar decisions")
            return decision_logs

        except Exception as e:
            logger.error(f"Failed to recall similar decisions: {e}", exc_info=True)
            return []
