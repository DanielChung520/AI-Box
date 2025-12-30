# 代碼功能說明: 緩存工具
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""緩存工具

提供緩存功能，支持內存緩存和可選的 Redis 緩存。
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class Cache:
    """簡單的內存緩存實現"""

    def __init__(self) -> None:
        """初始化緩存"""
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        獲取緩存值

        Args:
            key: 緩存鍵

        Returns:
            緩存值，如果不存在或已過期返回 None
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if entry["expires_at"] > time.time():
            return entry["value"]

        # 過期，刪除
        del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: float = 3600.0) -> None:
        """
        設置緩存值

        Args:
            key: 緩存鍵
            value: 緩存值
            ttl: 生存時間（秒），默認 3600 秒（1 小時）
        """
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl,
        }

    def delete(self, key: str) -> None:
        """
        刪除緩存值

        Args:
            key: 緩存鍵
        """
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        """清空所有緩存"""
        self._cache.clear()


def generate_cache_key(prefix: str, **kwargs: Any) -> str:
    """
    生成緩存鍵

    Args:
        prefix: 緩存鍵前綴
        **kwargs: 用於生成鍵的參數

    Returns:
        緩存鍵字符串
    """
    # 對參數進行排序以確保一致性
    sorted_params = sorted(kwargs.items())
    params_str = json.dumps(sorted_params, sort_keys=True, ensure_ascii=False)
    params_hash = hashlib.md5(params_str.encode()).hexdigest()
    return f"{prefix}:{params_hash}"


# 全局緩存實例（單例模式）
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """
    獲取緩存實例（單例模式）

    Returns:
        Cache 實例
    """
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
