# 代碼功能說明: AAM 核心管理器
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 核心管理器 - 提供記憶檢索、存儲、更新和刪除功能"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog

from agents.infra.memory.aam.models import Memory, MemoryType, MemoryPriority
from agents.infra.memory.aam.storage_adapter import (
    BaseStorageAdapter,
    RedisAdapter,
    ChromaDBAdapter,
    ArangoDBAdapter,
)

logger = structlog.get_logger(__name__)


class AAMManager:
    """AAM 管理器 - 管理記憶的存儲、檢索、更新和刪除"""

    def __init__(
        self,
        redis_adapter: Optional[RedisAdapter] = None,
        chromadb_adapter: Optional[ChromaDBAdapter] = None,
        arangodb_adapter: Optional[ArangoDBAdapter] = None,
        enable_short_term: bool = True,
        enable_long_term: bool = True,
        memory_priority_threshold: float = 0.7,
    ):
        """
        初始化 AAM 管理器

        Args:
            redis_adapter: Redis 適配器（短期記憶）
            chromadb_adapter: ChromaDB 適配器（長期記憶向量存儲）
            arangodb_adapter: ArangoDB 適配器（記憶關係圖）
            enable_short_term: 是否啟用短期記憶
            enable_long_term: 是否啟用長期記憶
            memory_priority_threshold: 記憶優先級閾值（高於此值的記憶優先檢索）
        """
        self.redis_adapter = redis_adapter
        self.chromadb_adapter = chromadb_adapter
        self.arangodb_adapter = arangodb_adapter
        self.enable_short_term = enable_short_term
        self.enable_long_term = enable_long_term
        self.memory_priority_threshold = memory_priority_threshold
        self.logger = logger.bind(component="aam_manager")

        # 驗證適配器配置
        if enable_short_term and redis_adapter is None:
            self.logger.warning(
                "Short-term memory enabled but Redis adapter not provided"
            )
        if enable_long_term and chromadb_adapter is None:
            self.logger.warning(
                "Long-term memory enabled but ChromaDB adapter not provided"
            )

    def _get_adapter(self, memory_type: MemoryType) -> Optional[BaseStorageAdapter]:
        """根據記憶類型獲取對應的適配器"""
        if memory_type == MemoryType.SHORT_TERM:
            if not self.enable_short_term:
                return None
            return self.redis_adapter
        elif memory_type == MemoryType.LONG_TERM:
            if not self.enable_long_term:
                return None
            return self.chromadb_adapter
        return None

    def store_memory(
        self,
        content: str,
        memory_type: MemoryType,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None,
        memory_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        存儲記憶

        Args:
            content: 記憶內容
            memory_type: 記憶類型
            priority: 記憶優先級
            metadata: 元數據
            memory_id: 記憶 ID（如果為 None 則自動生成）

        Returns:
            記憶 ID，如果失敗則返回 None
        """
        try:
            if memory_id is None:
                memory_id = str(uuid.uuid4())

            memory = Memory(
                memory_id=memory_id,
                content=content,
                memory_type=memory_type,
                priority=priority,
                metadata=metadata or {},
            )

            # 存儲到對應的適配器
            adapter = self._get_adapter(memory_type)
            if adapter is None:
                self.logger.warning(
                    "No adapter available for memory type",
                    memory_type=memory_type.value,
                )
                return None

            success = adapter.store(memory)
            if not success:
                return None

            # 如果啟用了 ArangoDB，也存儲到關係圖
            if self.arangodb_adapter is not None:
                self.arangodb_adapter.store(memory)

            self.logger.info(
                "Stored memory", memory_id=memory_id, memory_type=memory_type.value
            )
            return memory_id
        except Exception as e:
            self.logger.error("Failed to store memory", error=str(e))
            return None

    def retrieve_memory(
        self, memory_id: str, memory_type: Optional[MemoryType] = None
    ) -> Optional[Memory]:
        """
        檢索記憶

        Args:
            memory_id: 記憶 ID
            memory_type: 記憶類型（如果為 None 則在所有類型中搜索）

        Returns:
            記憶對象，如果不存在則返回 None
        """
        try:
            # 如果指定了記憶類型，直接從對應適配器檢索
            if memory_type is not None:
                adapter = self._get_adapter(memory_type)
                if adapter is None:
                    return None
                memory = adapter.retrieve(memory_id)
                if memory is not None:
                    memory.update_access()
                    return memory
                return None

            # 如果未指定類型，依次從各適配器檢索
            adapters: List[BaseStorageAdapter] = []
            if self.enable_short_term and self.redis_adapter is not None:
                adapters.append(self.redis_adapter)
            if self.enable_long_term and self.chromadb_adapter is not None:
                adapters.append(self.chromadb_adapter)

            for adapter in adapters:
                memory = adapter.retrieve(memory_id)
                if memory is not None:
                    memory.update_access()
                    return memory

            return None
        except Exception as e:
            self.logger.error(
                "Failed to retrieve memory", error=str(e), memory_id=memory_id
            )
            return None

    def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        priority: Optional[MemoryPriority] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新記憶

        Args:
            memory_id: 記憶 ID
            content: 新的記憶內容（如果為 None 則不更新）
            priority: 新的優先級（如果為 None 則不更新）
            metadata: 新的元數據（如果為 None 則不更新）

        Returns:
            是否成功更新
        """
        try:
            # 先檢索現有記憶
            memory = self.retrieve_memory(memory_id)
            if memory is None:
                self.logger.warning("Memory not found for update", memory_id=memory_id)
                return False

            # 更新字段
            if content is not None:
                memory.content = content
            if priority is not None:
                memory.priority = priority
            if metadata is not None:
                memory.metadata.update(metadata)

            from datetime import datetime

            memory.updated_at = datetime.now()

            # 更新到對應的適配器
            adapter = self._get_adapter(memory.memory_type)
            if adapter is None:
                return False

            success = adapter.update(memory)
            if success and self.arangodb_adapter is not None:
                self.arangodb_adapter.update(memory)

            self.logger.info("Updated memory", memory_id=memory_id)
            return success
        except Exception as e:
            self.logger.error(
                "Failed to update memory", error=str(e), memory_id=memory_id
            )
            return False

    def delete_memory(
        self, memory_id: str, memory_type: Optional[MemoryType] = None
    ) -> bool:
        """
        刪除記憶

        Args:
            memory_id: 記憶 ID
            memory_type: 記憶類型（如果為 None 則在所有類型中刪除）

        Returns:
            是否成功刪除
        """
        try:
            # 如果指定了記憶類型，直接從對應適配器刪除
            if memory_type is not None:
                adapter = self._get_adapter(memory_type)
                if adapter is None:
                    return False
                success = adapter.delete(memory_id)
                if success and self.arangodb_adapter is not None:
                    self.arangodb_adapter.delete(memory_id)
                return success

            # 如果未指定類型，依次從各適配器刪除
            adapters: List[BaseStorageAdapter] = []
            if self.enable_short_term and self.redis_adapter is not None:
                adapters.append(self.redis_adapter)
            if self.enable_long_term and self.chromadb_adapter is not None:
                adapters.append(self.chromadb_adapter)

            success = False
            for adapter in adapters:
                if adapter.delete(memory_id):
                    success = True

            if success and self.arangodb_adapter is not None:
                self.arangodb_adapter.delete(memory_id)

            self.logger.info("Deleted memory", memory_id=memory_id)
            return success
        except Exception as e:
            self.logger.error(
                "Failed to delete memory", error=str(e), memory_id=memory_id
            )
            return False

    def search_memories(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 10,
        min_relevance: float = 0.0,
    ) -> List[Memory]:
        """
        搜索記憶

        Args:
            query: 查詢文本
            memory_type: 記憶類型（如果為 None 則在所有類型中搜索）
            limit: 返回結果數量限制
            min_relevance: 最小相關度閾值

        Returns:
            記憶列表，按相關度排序
        """
        try:
            results: List[Memory] = []

            # 如果指定了記憶類型，只從對應適配器搜索
            if memory_type is not None:
                adapter = self._get_adapter(memory_type)
                if adapter is not None:
                    results = adapter.search(query, memory_type, limit)
            else:
                # 從所有適配器搜索並合併結果
                if self.enable_short_term and self.redis_adapter is not None:
                    short_term_results = self.redis_adapter.search(
                        query, MemoryType.SHORT_TERM, limit
                    )
                    results.extend(short_term_results)

                if self.enable_long_term and self.chromadb_adapter is not None:
                    long_term_results = self.chromadb_adapter.search(
                        query, MemoryType.LONG_TERM, limit
                    )
                    results.extend(long_term_results)

            # 過濾和排序
            filtered_results = [
                m for m in results if m.relevance_score >= min_relevance
            ]
            sorted_results = sorted(
                filtered_results,
                key=lambda m: (
                    m.relevance_score,
                    m.priority.value,
                    m.accessed_at.isoformat() if m.accessed_at else "",
                ),
                reverse=True,
            )

            # 限制結果數量
            return sorted_results[:limit]
        except Exception as e:
            self.logger.error("Failed to search memories", error=str(e))
            return []

    def sync_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        同步記憶到多個存儲適配器（實時更新）

        Args:
            memory_id: 記憶 ID
            content: 新的記憶內容（如果為 None 則不更新）
            metadata: 新的元數據（如果為 None 則不更新）

        Returns:
            是否成功同步
        """
        try:
            # 先檢索現有記憶
            memory = self.retrieve_memory(memory_id)
            if memory is None:
                self.logger.warning("Memory not found for sync", memory_id=memory_id)
                return False

            # 更新字段
            if content is not None:
                memory.content = content
            if metadata is not None:
                memory.metadata.update(metadata)

            from datetime import datetime

            memory.updated_at = datetime.now()

            # 同步到所有適配器
            success = True

            # 更新到主適配器
            adapter = self._get_adapter(memory.memory_type)
            if adapter is not None:
                if not adapter.update(memory):
                    success = False

            # 同步到 ArangoDB（如果啟用）
            if self.arangodb_adapter is not None:
                if not self.arangodb_adapter.update(memory):
                    self.logger.warning(
                        "Failed to sync memory to ArangoDB",
                        memory_id=memory_id,
                    )

            if success:
                self.logger.info("Synced memory", memory_id=memory_id)
            return success
        except Exception as e:
            self.logger.error(
                "Failed to sync memory", error=str(e), memory_id=memory_id
            )
            return False

    def incremental_update(
        self,
        memory_id: str,
        content_delta: Optional[str] = None,
        metadata_delta: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        增量更新記憶（僅更新變更部分）

        Args:
            memory_id: 記憶 ID
            content_delta: 內容增量（追加到現有內容）
            metadata_delta: 元數據增量（合併到現有元數據）

        Returns:
            是否成功更新
        """
        try:
            # 先檢索現有記憶
            memory = self.retrieve_memory(memory_id)
            if memory is None:
                self.logger.warning(
                    "Memory not found for incremental update", memory_id=memory_id
                )
                return False

            # 增量更新內容
            if content_delta is not None:
                memory.content += "\n" + content_delta

            # 增量更新元數據
            if metadata_delta is not None:
                memory.metadata.update(metadata_delta)

            from datetime import datetime

            memory.updated_at = datetime.now()

            # 更新到對應的適配器
            adapter = self._get_adapter(memory.memory_type)
            if adapter is None:
                return False

            success = adapter.update(memory)
            if success and self.arangodb_adapter is not None:
                self.arangodb_adapter.update(memory)

            self.logger.info("Incrementally updated memory", memory_id=memory_id)
            return success
        except Exception as e:
            self.logger.error(
                "Failed to incrementally update memory",
                error=str(e),
                memory_id=memory_id,
            )
            return False
