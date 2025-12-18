# 代碼功能說明: Redis 客戶端封裝
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 17:42:45 (UTC+8)

"""Redis 客戶端封裝，提供連線管理和單例模式。"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import structlog
import redis  # type: ignore[import-untyped]

logger = structlog.get_logger(__name__)

# 全局 Redis 客戶端實例
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
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

            # 修改時間：2025-12-12 - 檢查並修復 Redis slave 模式
            # 如果 Redis 被配置為 slave（只讀副本），自動將其改為 master 模式
            try:
                replication_info: Dict[str, Any] = _redis_client.info("replication")  # type: ignore[assignment]
                role = str(replication_info.get("role", "unknown"))

                if role == "slave":
                    logger.warning(
                        "Redis is configured as slave, converting to master",
                        master_host=replication_info.get("master_host"),
                        master_port=replication_info.get("master_port"),
                    )
                    # 停止複製，將 Redis 轉為 master 模式
                    _redis_client.slaveof()  # 無參數表示停止複製
                    logger.info("Redis successfully converted from slave to master")

                    # 驗證寫入權限
                    try:
                        test_key = "__redis_master_test__"
                        _redis_client.set(test_key, "test", ex=1)
                        _redis_client.delete(test_key)
                        logger.info("Redis write permission verified")
                    except redis.exceptions.ReadOnlyError:
                        logger.error(
                            "Redis is still read-only after conversion, manual intervention may be required"
                        )
                        raise RuntimeError(
                            "Redis is read-only and cannot be converted to master mode"
                        )
            except redis.exceptions.ReadOnlyError as e:
                # 如果 Redis 是只讀的，嘗試修復
                logger.warning(
                    "Redis is read-only, attempting to convert to master mode",
                    error=str(e),
                )
                try:
                    _redis_client.slaveof()  # 停止複製
                    logger.info("Redis read-only mode fixed")
                except Exception as fix_error:
                    logger.error(
                        "Failed to fix Redis read-only mode",
                        error=str(fix_error),
                    )
                    raise RuntimeError(
                        f"Redis is read-only and cannot be fixed: {fix_error}"
                    ) from fix_error
            except Exception as e:
                # 其他錯誤（如 info 命令失敗）不影響連接，只記錄警告
                logger.warning(
                    "Failed to check Redis replication status",
                    error=str(e),
                )

            # 獲取實際連接的主機和端口（用於日誌）
            # 如果使用 REDIS_URL，從 URL 中提取主機和端口；否則使用環境變數或默認值
            if redis_url:
                # 從 URL 解析主機和端口（例如：redis://localhost:6379/0）
                try:
                    from urllib.parse import urlparse

                    parsed = urlparse(redis_url)
                    actual_host = parsed.hostname or os.getenv(
                        "REDIS_HOST", "localhost"
                    )
                    actual_port = parsed.port or int(os.getenv("REDIS_PORT", "6379"))
                except Exception:
                    # 如果解析失敗，使用環境變數或默認值
                    actual_host = os.getenv("REDIS_HOST", "localhost")
                    actual_port = int(os.getenv("REDIS_PORT", "6379"))
            else:
                # 使用已定義的變數
                actual_host = redis_host
                actual_port = redis_port
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
