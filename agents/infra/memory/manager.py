# 代碼功能說明: Memory Manager 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Memory Manager - 實現短期和長期記憶管理"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

try:
    import redis  # type: ignore[import-untyped]  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, using in-memory storage")

from database.chromadb.client import ChromaDBClient
from agents.services.resource_controller import get_resource_controller

logger = logging.getLogger(__name__)


class MemoryManager:
    """記憶管理器 - 管理短期和長期記憶"""

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        chromadb_client: Optional[ChromaDBClient] = None,
        short_term_ttl: int = 3600,  # 1小時
    ):
        """
        初始化記憶管理器

        Args:
            redis_client: Redis 客戶端（用於短期記憶）
            chromadb_client: ChromaDB 客戶端（用於長期記憶）
            short_term_ttl: 短期記憶過期時間（秒）
        """
        self.redis_client = redis_client
        self.chromadb_client = chromadb_client
        self.short_term_ttl = short_term_ttl

        # 資源訪問控制器
        self._resource_controller = get_resource_controller()

        # 如果 Redis 不可用，使用內存存儲
        if not REDIS_AVAILABLE or redis_client is None:
            self._in_memory_storage: Dict[str, Any] = {}
            logger.warning("Using in-memory storage for short-term memory")

    def store_short_term(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        agent_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> bool:
        """
        存儲短期記憶

        Args:
            key: 記憶鍵
            value: 記憶值
            ttl: 過期時間（秒），如果為 None 則使用默認值
            agent_id: Agent ID（可選，用於權限檢查）
            namespace: 記憶命名空間（可選，用於權限檢查）

        Returns:
            是否成功存儲
        """
        # 資源訪問權限檢查
        if agent_id and namespace:
            if not self._resource_controller.check_memory_access(agent_id, namespace):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{namespace}'"
                )
                return False

        try:
            ttl = ttl or self.short_term_ttl

            if self.redis_client:
                # 使用 Redis
                serialized_value = (
                    json.dumps(value) if not isinstance(value, str) else value
                )
                self.redis_client.setex(key, ttl, serialized_value)
            else:
                # 使用內存存儲
                expire_time = datetime.now() + timedelta(seconds=ttl)
                self._in_memory_storage[key] = {
                    "value": value,
                    "expire_time": expire_time,
                }

            logger.debug(f"Stored short-term memory: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to store short-term memory: {e}")
            return False

    def retrieve_short_term(
        self,
        key: str,
        agent_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> Optional[Any]:
        """
        檢索短期記憶

        Args:
            key: 記憶鍵
            agent_id: Agent ID（可選，用於權限檢查）
            namespace: 記憶命名空間（可選，用於權限檢查）

        Returns:
            記憶值，如果不存在或已過期則返回 None
        """
        # 資源訪問權限檢查
        if agent_id and namespace:
            if not self._resource_controller.check_memory_access(agent_id, namespace):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{namespace}'"
                )
                return None

        try:
            if self.redis_client:
                # 從 Redis 檢索
                value = self.redis_client.get(key)
                if value:
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value.decode("utf-8")
                return None
            else:
                # 從內存存儲檢索
                if key in self._in_memory_storage:
                    item = self._in_memory_storage[key]
                    if datetime.now() < item["expire_time"]:
                        return item["value"]
                    else:
                        # 過期，刪除
                        del self._in_memory_storage[key]
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve short-term memory: {e}")
            return None

    def store_long_term(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        collection_name: str = "long_term_memory",
        agent_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        存儲長期記憶到向量數據庫

        Args:
            content: 記憶內容
            metadata: 元數據
            collection_name: 集合名稱（作為命名空間）
            agent_id: Agent ID（可選，用於權限檢查）

        Returns:
            記憶ID，如果失敗則返回 None
        """
        # 資源訪問權限檢查（collection_name 作為命名空間）
        if agent_id:
            if not self._resource_controller.check_memory_access(
                agent_id, collection_name
            ):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{collection_name}'"
                )
                return None

        try:
            if not self.chromadb_client:
                logger.warning(
                    "ChromaDB client not available, cannot store long-term memory"
                )
                return None

            # 構建完整的元數據
            full_metadata = {
                "timestamp": datetime.now().isoformat(),
                **(metadata or {}),
            }

            # 存儲到 ChromaDB
            memory_id = self.chromadb_client.add_document(  # type: ignore[attr-defined]
                collection_name=collection_name,
                content=content,
                metadata=full_metadata,
            )

            logger.debug(f"Stored long-term memory: {memory_id}")
            return memory_id
        except Exception as e:
            logger.error(f"Failed to store long-term memory: {e}")
            return None

    def retrieve_long_term(
        self,
        query: str,
        collection_name: str = "long_term_memory",
        n_results: int = 5,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        從向量數據庫檢索長期記憶

        Args:
            query: 查詢文本
            collection_name: 集合名稱（作為命名空間）
            n_results: 返回結果數量
            agent_id: Agent ID（可選，用於權限檢查）

        Returns:
            檢索結果列表
        """
        # 資源訪問權限檢查（collection_name 作為命名空間）
        if agent_id:
            if not self._resource_controller.check_memory_access(
                agent_id, collection_name
            ):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{collection_name}'"
                )
                return []

        try:
            if not self.chromadb_client:
                logger.warning(
                    "ChromaDB client not available, cannot retrieve long-term memory"
                )
                return []

            # 從 ChromaDB 檢索
            results = self.chromadb_client.query(  # type: ignore[attr-defined]
                collection_name=collection_name,
                query_text=query,
                n_results=n_results,
            )

            logger.debug(f"Retrieved {len(results)} long-term memories")
            return results
        except Exception as e:
            logger.error(f"Failed to retrieve long-term memory: {e}")
            return []

    def delete_short_term(
        self,
        key: str,
        agent_id: Optional[str] = None,
        namespace: Optional[str] = None,
    ) -> bool:
        """
        刪除短期記憶

        Args:
            key: 記憶鍵
            agent_id: Agent ID（可選，用於權限檢查）
            namespace: 記憶命名空間（可選，用於權限檢查）

        Returns:
            是否成功刪除
        """
        # 資源訪問權限檢查
        if agent_id and namespace:
            if not self._resource_controller.check_memory_access(agent_id, namespace):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{namespace}'"
                )
                return False

        try:
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                if key in self._in_memory_storage:
                    del self._in_memory_storage[key]

            logger.debug(f"Deleted short-term memory: {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete short-term memory: {e}")
            return False

    def clear_short_term(self, pattern: Optional[str] = None) -> int:
        """
        清空短期記憶

        Args:
            pattern: 鍵模式（僅 Redis 支持）

        Returns:
            刪除的鍵數量
        """
        try:
            if self.redis_client:
                if pattern:
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        return self.redis_client.delete(*keys)
                else:
                    # 清空所有鍵（謹慎使用）
                    return self.redis_client.flushdb()
            else:
                if pattern:
                    # 簡單的模式匹配
                    keys_to_delete = [
                        k for k in self._in_memory_storage.keys() if pattern in k
                    ]
                    for key in keys_to_delete:
                        del self._in_memory_storage[key]
                    return len(keys_to_delete)
                else:
                    count = len(self._in_memory_storage)
                    self._in_memory_storage.clear()
                    return count

            return 0
        except Exception as e:
            logger.error(f"Failed to clear short-term memory: {e}")
            return 0
