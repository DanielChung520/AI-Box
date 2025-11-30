# 代碼功能說明: AAM 混合 RAG 服務
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 混合 RAG 服務 - 實現向量檢索 + 圖檢索混合 RAG"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

import structlog

from agent_process.memory.aam.models import Memory
from agent_process.memory.aam.aam_core import AAMManager
from agent_process.memory.aam.realtime_retrieval import RealtimeRetrievalService

logger = structlog.get_logger(__name__)


class RetrievalStrategy(str, Enum):
    """檢索策略枚舉"""

    VECTOR_FIRST = "vector_first"  # 向量優先
    GRAPH_FIRST = "graph_first"  # 圖優先
    HYBRID = "hybrid"  # 混合


class HybridRAGService:
    """混合 RAG 服務 - 整合向量檢索和圖檢索"""

    def __init__(
        self,
        aam_manager: AAMManager,
        retrieval_service: Optional[RealtimeRetrievalService] = None,
        strategy: RetrievalStrategy = RetrievalStrategy.HYBRID,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
        max_workers: int = 4,
    ):
        """
        初始化混合 RAG 服務

        Args:
            aam_manager: AAM 管理器
            retrieval_service: 實時檢索服務
            strategy: 檢索策略
            vector_weight: 向量檢索權重
            graph_weight: 圖檢索權重
            max_workers: 並行檢索的最大工作線程數
        """
        self.aam_manager = aam_manager
        self.retrieval_service = retrieval_service or RealtimeRetrievalService(
            aam_manager
        )
        self.strategy = strategy
        self.vector_weight = vector_weight
        self.graph_weight = graph_weight
        self.max_workers = max_workers
        self.logger = logger.bind(component="hybrid_rag")

        # 結果緩存
        self._cache: Dict[str, tuple[float, List[Dict[str, Any]]]] = {}

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        strategy: Optional[RetrievalStrategy] = None,
        min_relevance: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        執行混合 RAG 檢索

        Args:
            query: 查詢文本
            top_k: 返回結果數量
            strategy: 檢索策略（如果為 None 則使用默認策略）
            min_relevance: 最小相關度閾值

        Returns:
            RAG 結果列表，格式為 [{"content": "...", "metadata": {...}, "score": ...}]
        """
        start_time = time.time()
        strategy = strategy or self.strategy

        try:
            # 根據策略執行檢索
            if strategy == RetrievalStrategy.VECTOR_FIRST:
                results = self._vector_first_retrieval(query, top_k, min_relevance)
            elif strategy == RetrievalStrategy.GRAPH_FIRST:
                results = self._graph_first_retrieval(query, top_k, min_relevance)
            else:  # HYBRID
                results = self._hybrid_retrieval(query, top_k, min_relevance)

            # 格式化結果供 LLM 使用
            formatted_results = self._format_for_llm(results)

            elapsed = (time.time() - start_time) * 1000
            self.logger.info(
                "Hybrid RAG retrieval completed",
                query=query[:50],
                count=len(formatted_results),
                strategy=strategy.value,
                elapsed_ms=elapsed,
            )

            return formatted_results
        except Exception as e:
            self.logger.error("Failed to perform hybrid RAG retrieval", error=str(e))
            return []

    def _vector_first_retrieval(
        self, query: str, top_k: int, min_relevance: float
    ) -> List[Memory]:
        """向量優先檢索"""
        # 先執行向量檢索
        vector_results = self.retrieval_service.retrieve(
            query, limit=top_k, min_relevance=min_relevance
        )

        # 如果結果不足，再執行圖檢索補充
        if len(vector_results) < top_k:
            graph_results = self._graph_retrieval(query, top_k - len(vector_results))
            vector_results.extend(graph_results)

        return vector_results[:top_k]

    def _graph_first_retrieval(
        self, query: str, top_k: int, min_relevance: float
    ) -> List[Memory]:
        """圖優先檢索"""
        # 先執行圖檢索
        graph_results = self._graph_retrieval(query, top_k)

        # 如果結果不足，再執行向量檢索補充
        if len(graph_results) < top_k:
            vector_results = self.retrieval_service.retrieve(
                query, limit=top_k - len(graph_results), min_relevance=min_relevance
            )
            graph_results.extend(vector_results)

        return graph_results[:top_k]

    def _hybrid_retrieval(
        self, query: str, top_k: int, min_relevance: float
    ) -> List[Memory]:
        """混合檢索（並行執行向量和圖檢索，然後融合結果）"""
        results: List[Memory] = []

        # 並行執行向量和圖檢索
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交向量檢索任務
            vector_future = executor.submit(
                self.retrieval_service.retrieve,
                query,
                limit=top_k * 2,
                min_relevance=min_relevance,
            )

            # 提交圖檢索任務
            graph_future = executor.submit(self._graph_retrieval, query, top_k * 2)

            # 收集結果
            vector_results = vector_future.result(timeout=5.0)
            graph_results = graph_future.result(timeout=5.0)

        # 融合結果（加權合併、去重、排序）
        results = self._merge_results(vector_results, graph_results, top_k)

        return results

    def _graph_retrieval(self, query: str, limit: int) -> List[Memory]:
        """圖檢索（基於 ArangoDB 知識圖譜）"""
        # TODO: 實現基於知識圖譜的檢索
        # 這裡先返回空列表，實際實現需要：
        # 1. 從知識圖譜中查詢相關實體
        # 2. 根據實體關係查找相關記憶
        # 3. 返回記憶列表
        self.logger.debug("Graph retrieval not fully implemented yet")
        return []

    def _merge_results(
        self, vector_results: List[Memory], graph_results: List[Memory], top_k: int
    ) -> List[Memory]:
        """合併向量和圖檢索結果"""
        # 去重（基於 memory_id）
        seen_ids: set[str] = set()
        merged: List[Memory] = []

        # 合併結果並應用權重
        for memory in vector_results:
            if memory.memory_id not in seen_ids:
                # 應用向量權重
                memory.relevance_score *= self.vector_weight
                merged.append(memory)
                seen_ids.add(memory.memory_id)

        for memory in graph_results:
            if memory.memory_id not in seen_ids:
                # 應用圖權重
                memory.relevance_score *= self.graph_weight
                merged.append(memory)
                seen_ids.add(memory.memory_id)
            else:
                # 如果已存在，增加相關度（融合）
                for m in merged:
                    if m.memory_id == memory.memory_id:
                        m.relevance_score += memory.relevance_score * self.graph_weight
                        break

        # 按相關度排序
        merged.sort(key=lambda m: m.relevance_score, reverse=True)

        return merged[:top_k]

    def _format_for_llm(self, memories: List[Memory]) -> List[Dict[str, Any]]:
        """格式化結果供 LLM 使用"""
        formatted = []
        for memory in memories:
            formatted.append(
                {
                    "content": memory.content,
                    "metadata": {
                        "memory_id": memory.memory_id,
                        "memory_type": memory.memory_type.value,
                        "priority": memory.priority.value,
                        **memory.metadata,
                    },
                    "score": memory.relevance_score,
                }
            )
        return formatted

    def update_strategy(self, strategy: RetrievalStrategy) -> None:
        """更新檢索策略"""
        self.strategy = strategy
        self.logger.info("Updated retrieval strategy", strategy=strategy.value)

    def update_weights(self, vector_weight: float, graph_weight: float) -> None:
        """更新檢索權重"""
        total = vector_weight + graph_weight
        if total > 0:
            self.vector_weight = vector_weight / total
            self.graph_weight = graph_weight / total
            self.logger.info(
                "Updated retrieval weights",
                vector_weight=self.vector_weight,
                graph_weight=self.graph_weight,
            )
