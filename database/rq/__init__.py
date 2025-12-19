# 代碼功能說明: RQ 任務隊列模組初始化
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ 任務隊列模組 - 提供任務隊列客戶端和 Worker 管理"""

from database.rq.queue import (
    FILE_PROCESSING_QUEUE,
    KG_EXTRACTION_QUEUE,
    VECTORIZATION_QUEUE,
    get_redis_connection,
    get_task_queue,
)

__all__ = [
    "get_task_queue",
    "get_redis_connection",
    "FILE_PROCESSING_QUEUE",
    "VECTORIZATION_QUEUE",
    "KG_EXTRACTION_QUEUE",
]
