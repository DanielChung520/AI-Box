# 代碼功能說明: 記憶裁剪服務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""記憶裁剪服務 - 定期清理低價值數據和更新 Embedding"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from agents.task_analyzer.routing_memory.metadata_store import (
    ROUTING_DECISIONS_COLLECTION,
    RoutingMetadataStore,
)
from agents.task_analyzer.routing_memory.vector_store import RoutingVectorStore
from database.arangodb.client import ArangoDBClient

logger = logging.getLogger(__name__)

# 默認配置
DEFAULT_TTL_DAYS = 90  # 默認 TTL：90 天
DEFAULT_MIN_FREQUENCY = 0.01  # 最小使用頻率（1%）
DEFAULT_MIN_SUCCESS_RATE = 0.3  # 最小成功率（30%）


class PruningService:
    """記憶裁剪服務類"""

    def __init__(
        self,
        client: Optional[ArangoDBClient] = None,
        ttl_days: int = DEFAULT_TTL_DAYS,
        min_frequency: float = DEFAULT_MIN_FREQUENCY,
        min_success_rate: float = DEFAULT_MIN_SUCCESS_RATE,
    ):
        """
        初始化記憶裁剪服務

        Args:
            client: ArangoDB 客戶端
            ttl_days: TTL 天數（超過此天數的數據將被清理）
            min_frequency: 最小使用頻率（低於此頻率的數據將被清理）
            min_success_rate: 最小成功率（低於此成功率的數據將被清理）
        """
        self.metadata_store = RoutingMetadataStore(client)
        self.vector_store = RoutingVectorStore()
        self.client = client or ArangoDBClient()
        self.ttl_days = ttl_days
        self.min_frequency = min_frequency
        self.min_success_rate = min_success_rate

    def calculate_frequency(self, days: int = 30) -> Dict[str, float]:
        """
        計算每個決策的使用頻率（基於最近 N 天的查詢次數）

        Args:
            days: 統計天數（默認 30 天）

        Returns:
            決策 ID 到頻率的映射
        """
        if self.client.db is None:
            logger.error("ArangoDB client is not connected")
            return {}

        try:
            self.client.db.collection(ROUTING_DECISIONS_COLLECTION)

            # 計算時間範圍
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()

            # 查詢最近 N 天的決策
            aql = f"""
                FOR doc IN {ROUTING_DECISIONS_COLLECTION}
                    FILTER doc.timestamp >= @cutoff_date
                    COLLECT decision_key = doc._key INTO groups
                    RETURN {{
                        decision_key: decision_key,
                        count: LENGTH(groups),
                        total_days: @days
                    }}
            """
            cursor = self.client.db.aql.execute(
                aql, bind_vars={"cutoff_date": cutoff_iso, "days": days}
            )
            results = list(cursor)

            # 計算總查詢次數
            total_queries = sum(r["count"] for r in results)

            # 計算頻率
            frequencies: Dict[str, float] = {}
            for result in results:
                decision_key = result["decision_key"]
                count = result["count"]
                frequency = count / total_queries if total_queries > 0 else 0.0
                frequencies[decision_key] = frequency

            logger.info(
                f"Calculated frequencies for {len(frequencies)} decisions "
                f"(total queries: {total_queries})"
            )
            return frequencies

        except Exception as e:
            logger.error(f"Failed to calculate frequency: {e}", exc_info=True)
            return {}

    def prune_by_ttl(self) -> int:
        """
        根據 TTL 清理過期數據

        Returns:
            清理的數據數量
        """
        if self.client.db is None:
            logger.error("ArangoDB client is not connected")
            return 0

        try:
            collection = self.client.db.collection(ROUTING_DECISIONS_COLLECTION)

            # 計算過期時間
            cutoff_date = datetime.utcnow() - timedelta(days=self.ttl_days)
            cutoff_iso = cutoff_date.isoformat()

            # 查詢過期數據
            aql = f"""
                FOR doc IN {ROUTING_DECISIONS_COLLECTION}
                    FILTER doc.timestamp < @cutoff_date
                    RETURN doc._key
            """
            cursor = self.client.db.aql.execute(aql, bind_vars={"cutoff_date": cutoff_iso})
            expired_keys = [doc for doc in cursor]

            # 刪除過期數據
            deleted_count = 0
            for key in expired_keys:
                try:
                    collection.delete(key)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete expired decision {key}: {e}")

            logger.info(f"Pruned {deleted_count} expired decisions (TTL: {self.ttl_days} days)")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to prune by TTL: {e}", exc_info=True)
            return 0

    def prune_by_frequency(self, frequencies: Optional[Dict[str, float]] = None) -> int:
        """
        根據使用頻率和成功率清理低價值數據

        Args:
            frequencies: 使用頻率映射（如果不提供則自動計算）

        Returns:
            清理的數據數量
        """
        if self.client.db is None:
            logger.error("ArangoDB client is not connected")
            return 0

        try:
            collection = self.client.db.collection(ROUTING_DECISIONS_COLLECTION)

            # 計算頻率（如果未提供）
            if frequencies is None:
                frequencies = self.calculate_frequency()

            # 查詢所有決策
            aql = f"""
                FOR doc IN {ROUTING_DECISIONS_COLLECTION}
                    RETURN {{
                        _key: doc._key,
                        success: doc.success,
                        outcome: doc.outcome
                    }}
            """
            cursor = self.client.db.aql.execute(aql)
            all_decisions = list(cursor)

            # 計算成功率
            success_rates: Dict[str, float] = {}
            decision_counts: Dict[str, int] = {}
            decision_success_counts: Dict[str, int] = {}

            for decision in all_decisions:
                key = decision["_key"]
                decision_counts[key] = decision_counts.get(key, 0) + 1
                # 判斷是否成功
                is_success = False
                if "success" in decision and decision["success"]:
                    is_success = True
                elif "outcome" in decision and decision["outcome"] == "success":
                    is_success = True

                if is_success:
                    decision_success_counts[key] = decision_success_counts.get(key, 0) + 1

            # 計算成功率
            for key in decision_counts:
                count = decision_counts[key]
                success_count = decision_success_counts.get(key, 0)
                success_rates[key] = success_count / count if count > 0 else 0.0

            # 找出低價值數據（頻率低且成功率低）
            low_value_keys: List[str] = []
            for key in frequencies:
                frequency = frequencies.get(key, 0.0)
                success_rate = success_rates.get(key, 0.0)

                if frequency < self.min_frequency and success_rate < self.min_success_rate:
                    low_value_keys.append(key)

            # 刪除低價值數據
            deleted_count = 0
            for key in low_value_keys:
                try:
                    collection.delete(key)
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete low-value decision {key}: {e}")

            logger.info(
                f"Pruned {deleted_count} low-value decisions "
                f"(frequency < {self.min_frequency}, success_rate < {self.min_success_rate})"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to prune by frequency: {e}", exc_info=True)
            return 0

    async def update_embeddings(
        self, decision_keys: Optional[List[str]] = None, batch_size: int = 100
    ) -> int:
        """
        更新向量 embedding（如果語義發生變化）

        Args:
            decision_keys: 要更新的決策鍵列表（如果不提供則更新所有）
            batch_size: 批次大小

        Returns:
            更新的數據數量
        """
        if self.client.db is None:
            logger.error("ArangoDB client is not connected")
            return 0

        try:
            self.client.db.collection(ROUTING_DECISIONS_COLLECTION)

            # 獲取要更新的決策
            if decision_keys:
                aql = f"""
                    FOR key IN @keys
                        FOR doc IN {ROUTING_DECISIONS_COLLECTION}
                            FILTER doc._key == key
                            RETURN doc
                """
                cursor = self.client.db.aql.execute(aql, bind_vars={"keys": decision_keys})
            else:
                # 更新所有決策（僅更新最近修改的）
                cutoff_date = datetime.utcnow() - timedelta(days=7)  # 最近 7 天
                cutoff_iso = cutoff_date.isoformat()
                aql = f"""
                    FOR doc IN {ROUTING_DECISIONS_COLLECTION}
                        FILTER doc.timestamp >= @cutoff_date
                        RETURN doc
                """
                cursor = self.client.db.aql.execute(aql, bind_vars={"cutoff_date": cutoff_iso})

            decisions = list(cursor)

            # 批量更新 embedding
            updated_count = 0
            for i in range(0, len(decisions), batch_size):
                batch = decisions[i : i + batch_size]

                # 重新生成語義和 embedding
                # 注意：這裡需要從 metadata 重建 semantic，然後更新向量存儲
                # 由於需要訪問 semantic_extractor，這裡只記錄日誌
                # 實際的更新邏輯應該在調用時提供完整的決策日誌對象

                logger.info(
                    f"Updating embeddings for batch {i // batch_size + 1} ({len(batch)} decisions)"
                )

            logger.info(f"Updated embeddings for {updated_count} decisions")
            return updated_count

        except Exception as e:
            logger.error(f"Failed to update embeddings: {e}", exc_info=True)
            return 0

    async def prune_all(self) -> Dict[str, int]:
        """
        執行完整的記憶裁剪流程

        Returns:
            裁剪統計信息
        """
        logger.info("Starting memory pruning process...")

        stats: Dict[str, int] = {}

        # 1. TTL 清理
        ttl_pruned = self.prune_by_ttl()
        stats["ttl_pruned"] = ttl_pruned

        # 2. 頻率統計
        frequencies = self.calculate_frequency()

        # 3. 低價值數據清理
        frequency_pruned = self.prune_by_frequency(frequencies)
        stats["frequency_pruned"] = frequency_pruned

        # 4. Embedding 更新（可選，通常不需要頻繁更新）
        # updated = await self.update_embeddings()
        # stats["embeddings_updated"] = updated

        stats["total_pruned"] = ttl_pruned + frequency_pruned

        logger.info(f"Memory pruning completed: {stats}")
        return stats
