# 代碼功能說明: Chat 響應緩存中間件（記憶體版）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""CacheMiddleware：get_cached_response / set_cached_response，後端先用記憶體 dict。"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CacheMiddleware:
    """緩存中間件（記憶體版，TTL 僅在 get 時檢查過期）。"""

    def __init__(self) -> None:
        # key -> (response_dict, expiry_timestamp)
        self._store: Dict[str, Tuple[Any, float]] = {}

    async def get_cached_response(
        self,
        key: str,
        ttl: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """
        獲取緩存響應；若過期或不存在則返回 None。

        Args:
            key: 緩存鍵
            ttl: 存活時間（秒），用於檢查過期（get 時與存入時對齊）

        Returns:
            緩存的 response 字典，或 None
        """
        import time as _time

        entry = self._store.get(key)
        if entry is None:
            return None
        data, expiry = entry
        if _time.time() > expiry:
            del self._store[key]
            return None
        return data

    async def set_cached_response(
        self,
        key: str,
        response: Dict[str, Any],
        ttl: int = 300,
    ) -> None:
        """
        設置緩存響應。

        Args:
            key: 緩存鍵
            response: 要緩存的響應字典
            ttl: 存活時間（秒）
        """
        import time as _time

        expiry = _time.time() + ttl
        self._store[key] = (response, expiry)
        logger.debug(f"Cache set: key={key[:16]}..., ttl={ttl}")


# 單例，供 dependencies 使用
_cache_middleware: Optional[CacheMiddleware] = None


def get_cache_middleware_instance() -> CacheMiddleware:
    """返回 CacheMiddleware 單例。"""
    global _cache_middleware
    if _cache_middleware is None:
        _cache_middleware = CacheMiddleware()
    return _cache_middleware
