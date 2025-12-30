# 代碼功能說明: 時間服務 - 緩存機制提供高精度時間
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""時間服務

提供高精度時間服務，使用緩存機制減少系統調用。

設計特點：
- 使用緩存機制，每 100ms 更新一次系統時間
- 使用 time.perf_counter() 計算經過的時間，提供高精度
- 線程安全（使用 Lock 保護共享狀態）
"""

from __future__ import annotations

import time
from datetime import datetime
from threading import Lock
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


class TimeService:
    """時間服務

    使用緩存機制提供高精度時間，減少系統調用開銷。
    """

    def __init__(self, cache_duration: float = 0.1) -> None:
        """
        初始化時間服務

        Args:
            cache_duration: 緩存持續時間（秒），默認 0.1 秒（100ms）
        """
        self._cached_time: float = time.time()
        self._last_update: float = time.perf_counter()
        self._cache_duration: float = cache_duration
        self._lock = Lock()

        logger.info(
            "time_service_initialized",
            cache_duration=cache_duration,
            initial_time=self._cached_time,
        )

    def now(self) -> float:
        """
        獲取當前時間（Unix 時間戳）

        使用緩存機制，每 cache_duration 秒更新一次系統時間，
        其餘時間使用 perf_counter 計算經過的時間。

        Returns:
            當前時間的 Unix 時間戳（浮點數）
        """
        with self._lock:
            elapsed = time.perf_counter() - self._last_update

            if elapsed > self._cache_duration:
                self._cached_time = time.time()
                self._last_update = time.perf_counter()
                elapsed = 0.0

            return self._cached_time + elapsed

    def now_datetime(self) -> datetime:
        """
        獲取當前時間（datetime 對象）

        Returns:
            當前時間的 datetime 對象（本地時區）
        """
        return datetime.fromtimestamp(self.now())

    def now_utc_datetime(self) -> datetime:
        """
        獲取當前時間（UTC datetime 對象）

        Returns:
            當前時間的 UTC datetime 對象
        """
        return datetime.utcfromtimestamp(self.now())


# 全局服務實例（單例模式）
_time_service: Optional[TimeService] = None


def get_time_service() -> TimeService:
    """
    獲取時間服務實例（單例模式）

    Returns:
        TimeService 實例
    """
    global _time_service

    if _time_service is None:
        _time_service = TimeService()

    return _time_service


# 向後兼容：保留舊的函數名
def get_smart_time_service() -> TimeService:
    """
    獲取時間服務實例（向後兼容別名）

    Returns:
        TimeService 實例
    """
    return get_time_service()
