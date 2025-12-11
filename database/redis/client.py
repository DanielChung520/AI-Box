# 代碼功能說明: Redis 客戶端封裝
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""Redis 客戶端封裝，提供連線管理和單例模式。"""

from __future__ import annotations

import os
from typing import Optional

import structlog
import redis  # type: ignore[import-untyped]

logger = structlog.get_logger(__name__)

# 全局 Redis 客戶端實例
_redis_client: Optional[redis.Redis[str]] = None


def get_redis_client() -> redis.Redis[str]:
    """獲取 Redis 客戶端實例（單例模式）。

    Returns:
        Redis 客戶端實例

    Raises:
        RuntimeError: 如果 Redis 連接失敗
    """
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            _redis_client = redis.Redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
        else:
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_password = os.getenv("REDIS_PASSWORD") or None

            _redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )

        # 測試連接
        try:
            _redis_client.ping()
            # 獲取實際連接的主機和端口（用於日誌）
            actual_host = redis_host if 'redis_host' in locals() else os.getenv("REDIS_HOST", "localhost")
            actual_port = redis_port if 'redis_port' in locals() else int(os.getenv("REDIS_PORT", "6379"))
            logger.info(
                "Redis connection established", host=actual_host, port=actual_port
            )
        except redis.ConnectionError as e:
            logger.error("Redis connection failed", error=str(e))
            raise RuntimeError(f"Failed to connect to Redis: {e}") from e

    return _redis_client


def reset_redis_client() -> None:
    """重置 Redis 客戶端實例（主要用於測試）。"""
    global _redis_client
    _redis_client = None
