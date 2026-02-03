# 代碼功能說明: Chat 請求限流（記憶體版，按 user_id 計數）
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""基於記憶體的簡單限流，按 user_id 計數，閾值可配置。"""

import logging
import time
from collections import defaultdict
from typing import DefaultDict

logger = logging.getLogger(__name__)

# 預設每分鐘請求上限
DEFAULT_LIMIT_PER_MINUTE = 60

# user_id -> [(timestamp, ), ...] 最近一分鐘內的請求時間戳
_buckets: DefaultDict[str, list] = defaultdict(list)


def check_rate_limit(
    user_id: str,
    limit_per_minute: int = DEFAULT_LIMIT_PER_MINUTE,
) -> None:
    """
    檢查是否超過限流閾值；超過則拋出異常。

    Args:
        user_id: 用戶 ID
        limit_per_minute: 每分鐘允許的請求數

    Raises:
        RuntimeError: 超過限流時拋出，message 含 retry_after 提示
    """
    now = time.time()
    window_start = now - 60.0
    bucket = _buckets[user_id]
    # 只保留最近一分鐘內的記錄
    bucket[:] = [t for t in bucket if t >= window_start]
    if len(bucket) >= limit_per_minute:
        oldest = min(bucket) if bucket else now
        retry_after = int(61 - (now - oldest))
        retry_after = max(1, min(retry_after, 60))
        logger.warning(
            f"Rate limit exceeded: user_id={user_id}, "
            f"count={len(bucket)}, limit={limit_per_minute}"
        )
        raise RuntimeError(f"請求過於頻繁，請在 {retry_after} 秒後重試")
    bucket.append(now)


def get_rate_limiter() -> object:
    """返回限流器對象（用於 Depends），提供 check_rate_limit 行為。"""
    return _RateLimiter()


class _RateLimiter:
    """限流器封裝，便於依賴注入。"""

    def __init__(self, limit_per_minute: int = DEFAULT_LIMIT_PER_MINUTE) -> None:
        self.limit_per_minute = limit_per_minute

    def check(self, user_id: str) -> None:
        """檢查 user_id 是否超過限流。"""
        check_rate_limit(user_id, self.limit_per_minute)
