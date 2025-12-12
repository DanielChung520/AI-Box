# 代碼功能說明: RQ 任務隊列客戶端
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ 任務隊列客戶端 - 封裝 RQ Queue 操作，提供任務隊列管理"""

from __future__ import annotations

import structlog
from rq import Queue

from database.redis import get_redis_client

logger = structlog.get_logger(__name__)

# 任務隊列名稱定義
FILE_PROCESSING_QUEUE = "file_processing"  # 文件處理隊列（分塊+向量化+圖譜）
VECTORIZATION_QUEUE = "vectorization"  # 向量化專用隊列
KG_EXTRACTION_QUEUE = "kg_extraction"  # 知識圖譜提取專用隊列

# 全局隊列實例（懶加載）
_queues: dict[str, Queue] = {}


def get_redis_connection():
    """獲取 RQ 使用的 Redis 連接。

    Returns:
        Redis 連接對象
    """
    # 直接使用 get_redis_client() 返回的 Redis 客戶端
    # RQ 可以直接使用 redis-py 的 Redis 客戶端
    redis_client = get_redis_client()
    return redis_client


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
