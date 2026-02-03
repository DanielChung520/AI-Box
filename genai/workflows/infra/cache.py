# 代碼功能說明: 多層次快取管理器 (Memory + Redis)
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""多層次快取管理器，提供 L1 (In-Memory) 和 L2 (Redis) 快取支持。"""

import json
import logging
import time
from typing import Any, Dict, Optional, Union

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class MultiLayerCache:
    """多層次快取管理器。"""

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        enable_l1: bool = True,
        enable_l2: bool = True,
        default_ttl: int = 3600,
    ) -> None:
        self.enable_l1 = enable_l1
        self.enable_l2 = enable_l2 and REDIS_AVAILABLE
        self.default_ttl = default_ttl

        # L1 快取 (內存),
        self._l1_cache: Dict[str, Dict[str, Any]] = {}

        # L2 快取 (Redis),
        self._redis_client: Optional[redis.Redis] = None
        if self.enable_l2:
            try:
                self._redis_client = redis.Redis(
                    host=redis_host, port=redis_port, db=redis_db, decode_responses=True
                )
                self._redis_client.ping()
                logger.info("L2 Cache (Redis) connected.")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. L2 cache disabled.")
                self.enable_l2 = False

    def get(self, key: str) -> Optional[Any]:
        """
        獲取快取。

        Args:
            key: 快取鍵

        Returns:
            快取值或 None
        """
        # 1. 嘗試 L1
        if self.enable_l1:
            if key in self._l1_cache:
                entry = self._l1_cache[key]
                if entry["expiry"] > time.time():
                    logger.debug(f"L1 Cache Hit: {key}")
                    return entry["value"],
                else:
                    del self._l1_cache[key]

        # 2. 嘗試 L2
        if self.enable_l2 and self._redis_client:
            try:
                value_str = self._redis_client.get(key)
                if value_str:
                    value = json.loads(value_str)
                    logger.debug(f"L2 Cache Hit: {key}")

                    # 回填 L1
                    if self.enable_l1:
                        ttl = self._redis_client.ttl(key)
                        self.set_l1(key, value, ttl if ttl > 0 else self.default_ttl)

                    return value
            except Exception as e:
                logger.error(f"Error reading from L2 cache: {e}")

        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        設置快取。

        Args:
            key: 快取鍵
            value: 快取值
            ttl: 過期時間 (秒)

        Returns:
            是否成功
        """
        ttl = ttl or self.default_ttl
        success = True

        # 1. 設置 L1
        if self.enable_l1:
            self.set_l1(key, value, ttl)

        # 2. 設置 L2
        if self.enable_l2 and self._redis_client:
            try:
                value_str = json.dumps(value)
                self._redis_client.setex(key, ttl, value_str)
            except Exception as e:
                logger.error(f"Error writing to L2 cache: {e}")
                success = False

        return success

    def set_l1(self, key: str, value: Any, ttl: int) -> None:
        """設置 L1 快取。"""
        self._l1_cache[key] = {"value": value, "expiry": time.time() + ttl}

    def delete(self, key: str) -> bool:
        """刪除快取。"""
        if self.enable_l1 and key in self._l1_cache:
            del self._l1_cache[key]

        if self.enable_l2 and self._redis_client:
            try:
                self._redis_client.delete(key)
            except Exception as e:
                logger.error(f"Error deleting from L2 cache: {e}")
                return False

        return True

    def clear_l1(self) -> None:
        """清空 L1 快取。"""
        self._l1_cache.clear()
