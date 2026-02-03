# 代碼功能說明: LLM 故障轉移機制實現
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""LLM 故障轉移機制，實現健康檢查、自動故障檢測和轉移、重試機制。"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agents.task_analyzer.models import LLMProvider

from .clients.base import BaseLLMClient
from .clients.factory import LLMClientFactory

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """健康檢查結果。"""

    provider: LLMProvider
    healthy: bool
    latency: float
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetryConfig:
    """重試配置。"""

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class LLMFailoverManager:
    """LLM 故障轉移管理器。"""

    def __init__(
        self,
        health_check_interval: float = 60.0,
        health_check_timeout: float = 5.0,
        failure_threshold: int = 3,
        retry_config: Optional[RetryConfig] = None,
    ):
        """
        初始化故障轉移管理器。

        Args:
            health_check_interval: 健康檢查間隔（秒）
            health_check_timeout: 健康檢查超時（秒）
            failure_threshold: 失敗閾值（連續失敗次數）
            retry_config: 重試配置
        """
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.failure_threshold = failure_threshold
        self.retry_config = retry_config or RetryConfig()

        # 提供商健康狀態
        self._provider_health: Dict[LLMProvider, HealthCheckResult] = {}
        self._failure_counts: Dict[LLMProvider, int] = {}
        self._last_health_check: Dict[LLMProvider, float] = {}

        # 健康檢查任務
        self._health_check_task: Optional[asyncio.Task[None]] = None
        self._running = False

    async def start(self) -> None:
        """啟動健康檢查任務。"""
        if self._running:
            return

        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("LLM failover manager started")

    async def stop(self) -> None:
        """停止健康檢查任務。"""
        self._running = False
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("LLM failover manager stopped")

    async def _health_check_loop(self) -> None:
        """健康檢查循環。"""
        while self._running:
            try:
                await self.check_all_providers()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Health check loop error: {exc}")

    async def check_provider_health(
        self,
        provider: LLMProvider,
        client: Optional[BaseLLMClient] = None,
    ) -> HealthCheckResult:
        """
        檢查提供商健康狀態。

        Args:
            provider: LLM 提供商
            client: 客戶端實例（可選，自動創建）

        Returns:
            健康檢查結果
        """
        start_time = time.time()

        try:
            if client is None:
                try:
                    client = LLMClientFactory.create_client(provider, use_cache=True)
                except Exception as exc:
                    latency = time.time() - start_time
                    logger.warning(f"Failed to create client for {provider.value}: {exc}")
                    return HealthCheckResult(
                        provider=provider,
                        healthy=False,
                        latency=latency,
                        error=f"Failed to create client: {exc}",
                    )

            if client is None:
                latency = time.time() - start_time
                return HealthCheckResult(
                    provider=provider,
                    healthy=False,
                    latency=latency,
                    error="Client is None",
                )

            if not client.is_available():
                latency = time.time() - start_time
                logger.debug(f"Client {provider.value} is not available")
                return HealthCheckResult(
                    provider=provider,
                    healthy=False,
                    latency=latency,
                    error="Client not available",
                )

            # 執行簡單的健康檢查（生成一個短文本）
            try:
                await asyncio.wait_for(
                    client.generate("test", max_tokens=5),
                    timeout=self.health_check_timeout,
                )
                latency = time.time() - start_time
                logger.debug(
                    f"Health check passed for {provider.value} " f"(latency: {latency:.3f}s)"
                )
                return HealthCheckResult(
                    provider=provider,
                    healthy=True,
                    latency=latency,
                )
            except asyncio.TimeoutError:
                latency = time.time() - start_time
                logger.warning(
                    f"Health check timeout for {provider.value} "
                    f"(timeout: {self.health_check_timeout}s)"
                )
                return HealthCheckResult(
                    provider=provider,
                    healthy=False,
                    latency=latency,
                    error="Health check timeout",
                )

        except Exception as exc:
            latency = time.time() - start_time
            # 健康檢查失敗屬預期（如無 API key、provider 離線），用 WARNING 避免日誌過度
            logger.warning(
                f"Health check failed for {provider.value}: {exc}",
            )
            return HealthCheckResult(
                provider=provider,
                healthy=False,
                latency=latency,
                error=str(exc),
            )

    async def check_all_providers(
        self,
        providers: Optional[List[LLMProvider]] = None,
    ) -> Dict[LLMProvider, HealthCheckResult]:
        """
        檢查所有提供商的健康狀態。

        Args:
            providers: 要檢查的提供商列表（可選，檢查所有）

        Returns:
            健康檢查結果字典
        """
        if providers is None:
            providers = list(LLMProvider)

        results: Dict[LLMProvider, HealthCheckResult] = {}

        # 並行檢查所有提供商
        tasks = [self.check_provider_health(provider) for provider in providers]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        for provider, result in zip(providers, check_results):
            if isinstance(result, Exception):
                # 異常情況：創建失敗的健康檢查結果
                health_result = HealthCheckResult(
                    provider=provider,
                    healthy=False,
                    latency=0.0,
                    error=str(result),
                )
                results[provider] = health_result
            else:
                # result 在 else 分支中一定是 HealthCheckResult
                assert isinstance(result, HealthCheckResult), "Expected HealthCheckResult"
                results[provider] = result
                health_result = result

            # 更新跟踪狀態（無論是異常還是正常結果）
            self._provider_health[provider] = health_result
            self._last_health_check[provider] = time.time()

            # 更新失敗計數
            if health_result.healthy:
                self._failure_counts[provider] = 0
            else:
                self._failure_counts[provider] = self._failure_counts.get(provider, 0) + 1

        return results

    def is_provider_healthy(self, provider: LLMProvider) -> bool:
        """
        檢查提供商是否健康。

        Args:
            provider: LLM 提供商

        Returns:
            如果健康返回 True
        """
        if provider not in self._provider_health:
            # 未知狀態視為健康（首次檢查前假設健康）
            logger.debug(f"Provider {provider.value} has no health check history")
            return True

        result = self._provider_health[provider]
        failure_count = self._failure_counts.get(provider, 0)

        # 檢查是否超過失敗閾值
        if failure_count >= self.failure_threshold:
            logger.debug(
                f"Provider {provider.value} exceeded failure threshold "
                f"({failure_count}/{self.failure_threshold})"
            )
            return False

        # 檢查健康檢查結果是否過期（超過2倍間隔）
        last_check = self._last_health_check.get(provider, 0)
        current_time = time.time()
        if current_time - last_check > self.health_check_interval * 2:
            # 過期視為健康（避免誤判，但記錄警告）
            logger.warning(
                f"Provider {provider.value} health check expired "
                f"({current_time - last_check:.1f}s ago, "
                f"threshold: {self.health_check_interval * 2}s)"
            )
            return True

        return result.healthy

    def get_healthy_providers(
        self,
        providers: Optional[List[LLMProvider]] = None,
    ) -> List[LLMProvider]:
        """
        獲取健康的提供商列表。

        Args:
            providers: 要檢查的提供商列表（可選，檢查所有）

        Returns:
            健康的提供商列表
        """
        if providers is None:
            providers = list(LLMProvider)

        return [provider for provider in providers if self.is_provider_healthy(provider)]

    async def execute_with_retry(
        self,
        func: Callable[[LLMProvider], Any],
        provider: LLMProvider,
        fallback_providers: Optional[List[LLMProvider]] = None,
    ) -> Any:
        """
        執行函數並在失敗時重試或故障轉移。

        Args:
            func: 要執行的異步函數，接受 LLMProvider 作為參數
            provider: 主要提供商
            fallback_providers: 備用提供商列表（可選）

        Returns:
            函數執行結果

        Raises:
            Exception: 如果所有重試和故障轉移都失敗
        """
        config = self.retry_config
        last_exception: Optional[Exception] = None

        # 重試主提供商
        for attempt in range(config.max_retries):
            try:
                return await func(provider)
            except Exception as exc:
                last_exception = exc
                if attempt < config.max_retries - 1:
                    # 計算延遲（指數退避）
                    delay = min(
                        config.initial_delay * (config.exponential_base**attempt),
                        config.max_delay,
                    )
                    if config.jitter:
                        import random

                        # Jitter: 在 0.5x 到 1.0x 之間隨機調整延遲
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1} failed for {provider.value}, "
                        f"retrying in {delay:.2f}s: {exc}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retries exhausted for {provider.value}: {exc}")

        # 如果重試失敗，嘗試故障轉移到備用提供商
        if fallback_providers:
            for fallback in fallback_providers:
                if fallback == provider:
                    continue

                if not self.is_provider_healthy(fallback):
                    logger.debug(f"Skipping {fallback.value} (not healthy or already checked)")
                    continue

                try:
                    logger.info(f"Failing over to {fallback.value}")
                    # 使用 fallback provider 重新執行函數
                    return await func(fallback)
                except Exception as exc:
                    logger.warning(f"Fallback to {fallback.value} also failed: {exc}")
                    last_exception = exc
                    continue

        # 所有嘗試都失敗
        if last_exception:
            raise last_exception
        raise Exception("All providers failed")

    def get_provider_health_status(
        self,
    ) -> Dict[LLMProvider, Dict[str, Any]]:
        """
        獲取所有提供商的健康狀態。

        Returns:
            健康狀態字典
        """
        status: Dict[LLMProvider, Dict[str, Any]] = {}

        for provider in LLMProvider:
            result = self._provider_health.get(provider)
            failure_count = self._failure_counts.get(provider, 0)
            last_check = self._last_health_check.get(provider, 0)

            status[provider] = {
                "healthy": self.is_provider_healthy(provider),
                "failure_count": failure_count,
                "last_check": last_check,
                "latency": result.latency if result else None,
                "error": result.error if result else None,
            }

        return status
