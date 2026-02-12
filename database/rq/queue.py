# 代碼功能說明: RQ 任務隊列客戶端
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 22:41:48 (UTC+8)

"""RQ 任務隊列客戶端 - 封裝 RQ Queue 操作，提供任務隊列管理"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from rq import Queue

# 任務隊列名稱定義
FILE_PROCESSING_QUEUE = "file_processing"  # 文件處理隊列（分塊+向量化+圖譜）
VECTORIZATION_QUEUE = "vectorization"  # 向量化專用隊列
KG_EXTRACTION_QUEUE = "kg_extraction"  # 知識圖譜提取專用隊列
AGENT_TODO_QUEUE = "agent_todo"  # Agent-todo 非同步執行隊列
TASK_DELETION_QUEUE = "task_deletion"  # 任務刪除專用隊列

# 全局隊列實例（懶加載）
_queues: dict[str, Queue] = {}


def get_redis_connection():
    """獲取 RQ 使用的 Redis 連接。

    Returns:
        Redis 連接對象
    """
    # 修改時間：2025-12-12 - RQ 需要二進制模式（decode_responses=False）
    # 因為 RQ 使用 pickle 序列化任務數據，需要原始字節數據
    # 創建一個新的 Redis 連接，不使用 decode_responses
    import os

    import redis

    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        # 從 URL 創建連接，但不設置 decode_responses
        redis_conn = redis.Redis.from_url(
            redis_url,
            decode_responses=False,  # RQ 需要二進制模式
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    else:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD") or None

        redis_conn = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=False,  # RQ 需要二進制模式
            socket_connect_timeout=5,
            socket_timeout=5,
        )

    return redis_conn


def get_task_queue(queue_name: str = FILE_PROCESSING_QUEUE) -> Queue:
    """獲取任務隊列實例（單例模式）。

    Args:
        queue_name: 隊列名稱，默認為 'file_processing'

    Returns:
        RQ Queue 實例

    Raises:
        RuntimeError: 如果 Redis 連接失敗
    """
    global _queues

    if queue_name not in _queues:
        try:
            try:
                from rq import Queue
            except ImportError as exc:
                raise RuntimeError(
                    "RQ is not installed. Please install it first: pip install rq"
                ) from exc

            redis_conn = get_redis_connection()
            _queues[queue_name] = Queue(queue_name, connection=redis_conn)
            logger.info("RQ queue created", queue_name=queue_name)
        except Exception as e:
            logger.error(
                "Failed to create RQ queue",
                queue_name=queue_name,
                error=str(e),
            )
            raise RuntimeError(f"Failed to create RQ queue '{queue_name}': {e}") from e

    return _queues[queue_name]


def reset_queues() -> None:
    """重置所有隊列實例（主要用於測試）。"""
    global _queues
    _queues = {}
