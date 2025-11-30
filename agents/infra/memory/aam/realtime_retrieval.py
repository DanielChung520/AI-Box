# 代碼功能說明: AAM 實時檢索服務
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 實時檢索服務 - 提供實時記憶檢索、相關度計算和排序功能"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor

import structlog

from agents.infra.memory.aam.models import Memory, MemoryType, MemoryPriority
from agents.infra.memory.aam.aam_core import AAMManager

logger = structlog.get_logger(__name__)


class RealtimeRetrievalService:
    """實時檢索服務 - 提供基於對話上下文的實時記憶檢索"""

    def __init__(
        self,
        aam_manager: AAMManager,
        cache_enabled: bool = True,
        cache_ttl: int = 300,  # 5分鐘
        max_workers: int = 4,
    ):
        """
        初始化實時檢索服務

        Args:
            aam_manager: AAM 管理器實例
            cache_enabled: 是否啟用緩存
            cache_ttl: 緩存過期時間（秒）
            max_workers: 並行檢索的最大工作線程數
        """
        self.aam_manager = aam_manager
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
        self.max_workers = max_workers
        self.logger = logger.bind(component="realtime_retrieval")

        # 簡單的內存緩存（生產環境應使用 Redis）
        self._cache: Dict[str, tuple[float, List[Memory]]] = {}

    def _get_cache_key(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """生成緩存鍵"""
        context_str = str(sorted(context.items())) if context else ""
        return f"{query}:{context_str}"

    def _get_cached_results(self, cache_key: str) -> Optional[List[Memory]]:
        """從緩存獲取結果"""
        if not self.cache_enabled:
            return None

        if cache_key in self._cache:
            timestamp, results = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                self.logger.debug("Cache hit", cache_key=cache_key[:50])
                return results
            else:
                # 緩存過期，刪除
                del self._cache[cache_key]

        return None

    def _set_cached_results(self, cache_key: str, results: List[Memory]) -> None:
        """設置緩存結果"""
        if not self.cache_enabled:
            return

        self._cache[cache_key] = (time.time(), results)
        self.logger.debug("Cache set", cache_key=cache_key[:50])

    def _calculate_relevance(
        self, memory: Memory, query: str, context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        計算記憶相關度

        Args:
            memory: 記憶對象
            query: 查詢文本
            context: 上下文信息

        Returns:
            相關度分數（0.0-1.0）
        """
        # 基礎相關度（使用記憶的現有相關度分數）
        relevance = memory.relevance_score

        # 基於優先級的調整
        priority_weights = {
            MemoryPriority.CRITICAL: 0.3,
            MemoryPriority.HIGH: 0.2,
            MemoryPriority.MEDIUM: 0.1,
            MemoryPriority.LOW: 0.0,
        }
        relevance += priority_weights.get(memory.priority, 0.0)

        # 基於訪問頻率的調整
        if memory.access_count > 0:
            access_bonus = min(0.1, memory.access_count * 0.01)
            relevance += access_bonus

        # 基於時間的衰減（最近訪問的記憶相關度更高）
        if memory.accessed_at is not None:
            time_diff = time.time() - memory.accessed_at.timestamp()
            time_bonus = max(0.0, 0.1 * (1.0 - time_diff / 86400))  # 24小時衰減
            relevance += time_bonus

        # 確保相關度在 0.0-1.0 範圍內
        relevance = max(0.0, min(1.0, relevance))

        return relevance

    def _sort_memories(
        self,
        memories: List[Memory],
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Memory]:
        """
        對記憶進行排序

        Args:
            memories: 記憶列表
            query: 查詢文本
            context: 上下文信息

        Returns:
            排序後的記憶列表
        """
        # 計算每個記憶的相關度
        for memory in memories:
            memory.relevance_score = self._calculate_relevance(memory, query, context)

        # 按相關度、優先級、訪問時間排序
        sorted_memories = sorted(
            memories,
            key=lambda m: (
                m.relevance_score,
                m.priority.value,
                m.accessed_at.timestamp() if m.accessed_at else 0.0,
            ),
            reverse=True,
        )

        return sorted_memories

    def retrieve(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        min_relevance: float = 0.0,
        use_cache: bool = True,
    ) -> List[Memory]:
        """
        實時檢索記憶

        Args:
            query: 查詢文本
            context: 上下文信息（當前對話上下文）
            memory_type: 記憶類型（如果為 None 則在所有類型中搜索）
            limit: 返回結果數量限制
            min_relevance: 最小相關度閾值
            use_cache: 是否使用緩存

        Returns:
            記憶列表，按相關度排序
        """
        start_time = time.time()

        # 檢查緩存
        if use_cache:
            cache_key = self._get_cache_key(query, context)
            cached_results = self._get_cached_results(cache_key)
            if cached_results is not None:
                elapsed = (time.time() - start_time) * 1000
                self.logger.info(
                    "Retrieved from cache",
                    query=query[:50],
                    count=len(cached_results),
                    elapsed_ms=elapsed,
                )
                return cached_results[:limit]

        # 執行檢索
        if memory_type is not None:
            # 單一類型檢索
            results = self.aam_manager.search_memories(
                query, memory_type, limit=limit * 2, min_relevance=min_relevance
            )
        else:
            # 並行檢索多種類型
            results = self._parallel_search(query, limit * 2, min_relevance)

        # 計算相關度並排序
        sorted_results = self._sort_memories(results, query, context)

        # 過濾和限制結果
        filtered_results = [
            m for m in sorted_results if m.relevance_score >= min_relevance
        ][:limit]

        # 更新訪問信息
        for memory in filtered_results:
            memory.update_access()

        # 緩存結果
        if use_cache:
            cache_key = self._get_cache_key(query, context)
            self._set_cached_results(cache_key, filtered_results)

        elapsed = (time.time() - start_time) * 1000
        self.logger.info(
            "Retrieved memories",
            query=query[:50],
            count=len(filtered_results),
            elapsed_ms=elapsed,
        )

        return filtered_results

    def _parallel_search(
        self, query: str, limit: int, min_relevance: float
    ) -> List[Memory]:
        """並行檢索多種類型的記憶"""
        results: List[Memory] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []

            # 提交短期記憶檢索任務
            if self.aam_manager.enable_short_term:
                future = executor.submit(
                    self.aam_manager.search_memories,
                    query,
                    MemoryType.SHORT_TERM,
                    limit,
                    min_relevance,
                )
                futures.append(("short_term", future))

            # 提交長期記憶檢索任務
            if self.aam_manager.enable_long_term:
                future = executor.submit(
                    self.aam_manager.search_memories,
                    query,
                    MemoryType.LONG_TERM,
                    limit,
                    min_relevance,
                )
                futures.append(("long_term", future))

            # 收集結果
            for memory_type_name, future in futures:
                try:
                    type_results = future.result(timeout=5.0)
                    results.extend(type_results)
                    self.logger.debug(
                        "Retrieved memories from adapter",
                        adapter=memory_type_name,
                        count=len(type_results),
                    )
                except Exception as e:
                    self.logger.error(
                        "Failed to retrieve memories from adapter",
                        adapter=memory_type_name,
                        error=str(e),
                    )

        return results

    def clear_cache(self) -> int:
        """清空緩存"""
        count = len(self._cache)
        self._cache.clear()
        self.logger.info("Cache cleared", count=count)
        return count
