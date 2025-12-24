# 代碼功能說明: 存儲抽象層
# 創建日期: 2025-01-27 14:00 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 14:00 (UTC+8)

"""存儲抽象層，提供統一的存儲接口。"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import redis  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """存儲後端抽象基類。"""

    @abstractmethod
    def save(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        保存數據。

        Args:
            key: 鍵
            value: 值
            ttl: TTL 秒數（可選）

        Returns:
            是否成功保存
        """
        pass

    @abstractmethod
    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """
        加載數據。

        Args:
            key: 鍵

        Returns:
            數據，如果不存在則返回 None
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        刪除數據。

        Args:
            key: 鍵

        Returns:
            是否成功刪除
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        檢查鍵是否存在。

        Args:
            key: 鍵

        Returns:
            是否存在
        """
        pass

    @abstractmethod
    def list_keys(self, pattern: str = "*") -> List[str]:
        """
        列出匹配模式的鍵。

        Args:
            pattern: 模式（支持通配符）

        Returns:
            鍵列表
        """
        pass


class RedisStorageBackend(StorageBackend):
    """Redis 存儲後端實現。"""

    def __init__(self, redis_url: str, decode_responses: bool = True) -> None:
        """
        初始化 Redis 存儲後端。

        Args:
            redis_url: Redis 連接 URL
            decode_responses: 是否解碼響應
        """
        try:
            self._redis: Optional[redis.Redis] = redis.Redis.from_url(
                redis_url, decode_responses=decode_responses
            )
            self._redis.ping()
            logger.info("Redis storage backend initialized")
        except Exception as exc:
            logger.error("Failed to initialize Redis storage backend: %s", exc)
            raise

    def save(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """保存數據到 Redis。"""
        if self._redis is None:
            return False
        try:
            value_json = json.dumps(value, default=str)
            if ttl is not None:
                self._redis.setex(key, ttl, value_json)
            else:
                self._redis.set(key, value_json)
            return True
        except Exception as exc:
            logger.error("Failed to save to Redis: %s", exc)
            return False

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """從 Redis 加載數據。"""
        if self._redis is None:
            return None
        try:
            value_json = self._redis.get(key)
            if value_json is None:
                return None
            if isinstance(value_json, bytes):
                value_json = value_json.decode("utf-8")
            if isinstance(value_json, str):
                return json.loads(value_json)
            return None
        except Exception as exc:
            logger.error("Failed to load from Redis: %s", exc)
            return None

    def delete(self, key: str) -> bool:
        """從 Redis 刪除數據。"""
        if self._redis is None:
            return False
        try:
            return bool(self._redis.delete(key))
        except Exception as exc:
            logger.error("Failed to delete from Redis: %s", exc)
            return False

    def exists(self, key: str) -> bool:
        """檢查 Redis 中鍵是否存在。"""
        if self._redis is None:
            return False
        try:
            return bool(self._redis.exists(key))
        except Exception as exc:
            logger.error("Failed to check existence in Redis: %s", exc)
            return False

    def list_keys(self, pattern: str = "*") -> List[str]:
        """列出 Redis 中匹配模式的鍵。"""
        if self._redis is None:
            return []
        try:
            keys = self._redis.keys(pattern)
            if isinstance(keys, list):
                return keys
            if keys:
                return list(keys)  # type: ignore[arg-type]
            return []
        except Exception as exc:
            logger.error("Failed to list keys from Redis: %s", exc)
            return []


class MemoryStorageBackend(StorageBackend):
    """內存存儲後端實現。"""

    def __init__(self) -> None:
        """初始化內存存儲後端。"""
        self._store: Dict[str, Dict[str, Any]] = {}
        logger.info("Memory storage backend initialized")

    def save(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """保存數據到內存。"""
        try:
            self._store[key] = value
            return True
        except Exception as exc:
            logger.error("Failed to save to memory: %s", exc)
            return False

    def load(self, key: str) -> Optional[Dict[str, Any]]:
        """從內存加載數據。"""
        return self._store.get(key)

    def delete(self, key: str) -> bool:
        """從內存刪除數據。"""
        try:
            if key in self._store:
                del self._store[key]
                return True
            return False
        except Exception as exc:
            logger.error("Failed to delete from memory: %s", exc)
            return False

    def exists(self, key: str) -> bool:
        """檢查內存中鍵是否存在。"""
        return key in self._store

    def list_keys(self, pattern: str = "*") -> List[str]:
        """列出內存中匹配模式的鍵。"""
        if pattern == "*":
            return list(self._store.keys())
        # 簡單的模式匹配（支持 * 通配符）
        regex = re.compile(pattern.replace("*", ".*"))
        return [key for key in self._store.keys() if regex.match(key)]
