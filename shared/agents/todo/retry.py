# 代碼功能說明: Agent Todo 重試策略
# 創建日期: 2026-02-07
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-07

"""Agent Todo 重試策略（指數退避）"""

import asyncio
import random
from typing import Optional, Callable, Any
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RetryPolicy(str, Enum):
    """重試策略"""

    NONE = "NONE"
    LINEAR = "LINEAR"
    EXPONENTIAL_BACKOFF = "EXPONENTIAL_BACKOFF"
    EXPONENTIAL_JITTER = "EXPONENTIAL_JITTER"


class RetryResult(BaseModel):
    """重試結果"""

    success: bool
    attempts: int
    total_time: float
    last_error: Optional[str] = None
    result: Optional[Any] = None


class RetryConfig(BaseModel):
    """重試配置"""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1
    retryable_exceptions: list = []


class RetryPolicy:
    """重試策略管理器"""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def calculate_delay(self, attempt: int) -> float:
        """計算延遲時間"""
        if self.config.backoff_factor == 0:
            return self.config.initial_delay

        delay = self.config.initial_delay * (self.config.backoff_factor**attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)

        return delay

    async def execute(self, func: Callable, *args, **kwargs) -> RetryResult:
        """執行帶重試的函數"""
        start_time = datetime.utcnow()
        last_error = None

        for attempt in range(self.config.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                total_time = (datetime.utcnow() - start_time).total_seconds()

                logger.info(
                    f"Retry: {func.__name__} succeeded on attempt {attempt + 1}/{self.config.max_attempts}"
                )

                return RetryResult(
                    success=True,
                    attempts=attempt + 1,
                    total_time=total_time,
                    result=result,
                )

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Retry: {func.__name__} failed on attempt {attempt + 1}/{self.config.max_attempts}: {e}"
                )

                if attempt < self.config.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.info(f"Retry: Waiting {delay:.2f}s before next attempt")
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Retry: {func.__name__} failed after {self.config.max_attempts} attempts"
                    )

        total_time = (datetime.utcnow() - start_time).total_seconds()

        return RetryResult(
            success=False,
            attempts=self.config.max_attempts,
            total_time=total_time,
            last_error=last_error,
        )

    def should_retry(self, error: Exception) -> bool:
        """判斷是否應該重試"""
        if not self.config.retryable_exceptions:
            return True

        return any(isinstance(error, exc_type) for exc_type in self.config.retryable_exceptions)


class CircuitBreaker:
    """熔斷器"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure = None
        self.state = "CLOSED"

    def record_failure(self):
        """記錄失敗"""
        self.failure_count += 1
        self.last_failure = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker: OPENED after {self.failure_count} failures")

    def record_success(self):
        """記錄成功"""
        self.failure_count = 0
        self.last_failure = None
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        """判斷是否可以執行"""
        if self.state == "CLOSED":
            return True

        if self.state == "OPEN":
            if self.last_failure:
                elapsed = (datetime.utcnow() - self.last_failure).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info("Circuit breaker: HALF_OPEN (testing)")
                    return True
            return False

        return True

    def get_state(self) -> str:
        """取得當前狀態"""
        return self.state


class RetryWithCircuitBreaker:
    """帶熔斷的重試包裝器"""

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        self.retry_policy = RetryPolicy(retry_config)
        self.circuit_breaker = circuit_breaker or CircuitBreaker()

    async def execute(self, func: Callable, *args, **kwargs) -> RetryResult:
        """執行帶重試和熔斷的函數"""
        if not self.circuit_breaker.can_execute():
            return RetryResult(
                success=False,
                attempts=0,
                total_time=0,
                last_error=f"Circuit breaker: {self.circuit_breaker.get_state()}",
            )

        result = await self.retry_policy.execute(func, *args, **kwargs)

        if result.success:
            self.circuit_breaker.record_success()
        else:
            self.circuit_breaker.record_failure()

        return result
