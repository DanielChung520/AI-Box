# 代碼功能說明: Memory Manager 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-27

"""Memory Manager - 實現短期和長期記憶管理（使用 Qdrant）"""

import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

if TYPE_CHECKING:
    from database.qdrant.client import get_qdrant_client

try:
    import redis  # type: ignore[import-untyped]  # noqa: F401

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available, using in-memory storage")

from agents.services.resource_controller import get_resource_controller

QDRANT_AVAILABLE = False

try:
    from database.qdrant.client import get_qdrant_client

    # 測試 Qdrant 連接
    _qdrant = get_qdrant_client()
    _qdrant.get_collections()
    QDRANT_AVAILABLE = True
except ImportError:
    get_qdrant_client = None  # type: ignore[assignment]
    logging.warning("Qdrant not available, long-term memory will be disabled")
except Exception as e:
    get_qdrant_client = None  # type: ignore[assignment]
    logging.warning(f"Qdrant not available: {e}, long-term memory will be disabled")

logger = logging.getLogger(__name__)


class MemoryManager:
    """記憶管理器 - 管理短期和長期記憶"""

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        qdrant_client: Optional[QdrantClient] = None,
        short_term_ttl: int = 3600,  # 1小時
    ):
        """
        初始化記憶管理器

        Args:
            redis_client: Redis 客戶端（用於短期記憶）
            qdrant_client: Qdrant 客戶端（用於長期記憶向量存儲）
            short_term_ttl: 短期記憶過期時間（秒）
        """
        self.redis_client = redis_client
        self.qdrant_client = qdrant_client
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
                serialized_value = json.dumps(value) if not isinstance(value, str) else value
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
        存儲長期記憶到 Qdrant 向量數據庫

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
            if not self._resource_controller.check_memory_access(agent_id, collection_name):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{collection_name}'"
                )
                return None

        try:
            if not self.qdrant_client:
                logger.warning("Qdrant client not available, cannot store long-term memory")
                return None

            # 確保集合存在
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            if collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config={"size": 1536, "distance": "Cosine"},  # 默認向量配置
                )

            # 構建完整的元數據
            full_metadata = {
                "timestamp": datetime.now().isoformat(),
                **(metadata or {}),
            }

            # 使用簡單的 ID（實際應該使用向量嵌入）
            import uuid

            memory_id = str(uuid.uuid4())

            # 存儲到 Qdrant（這裡存儲原文而非向量，用於簡單場景）
            # 實際生產環境應該先將 content 轉為向量
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=[
                    {
                        "id": memory_id,
                        "vector": [0.0] * 1536,  # 佔位向量，實際應使用 embedding
                        "payload": {
                            "content": content,
                            **full_metadata,
                        },
                    }
                ],
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
        從 Qdrant 向量數據庫檢索長期記憶

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
            if not self._resource_controller.check_memory_access(agent_id, collection_name):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to access memory namespace '{collection_name}'"
                )
                return []

        try:
            if not self.qdrant_client:
                logger.warning("Qdrant client not available, cannot retrieve long-term memory")
                return []

            # 檢查集合是否存在
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            if collection_name not in collection_names:
                logger.debug(f"Collection '{collection_name}' does not exist")
                return []

            # 從 Qdrant 檢索（簡單實現，實際應使用向量搜索）
            # 注意：這裡使用簡單的過濾查詢，生產環境應該使用向量相似度搜索
            results = self.qdrant_client.scroll(
                collection_name=collection_name,
                limit=n_results,
                with_payload=True,
                with_vectors=False,
            )

            # 格式化結果
            formatted_results = []
            if results[0]:
                for point in results[0]:
                    formatted_results.append(
                        {
                            "id": point.id,
                            "content": point.payload.get("content", ""),
                            "metadata": {k: v for k, v in point.payload.items() if k != "content"},
                            "score": 1.0,  # 佔位分數
                        }
                    )

            logger.debug(f"Retrieved {len(formatted_results)} long-term memories")
            return formatted_results
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
                    keys_to_delete = [k for k in self._in_memory_storage.keys() if pattern in k]
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
