# 代碼功能說明: LLM 故障轉移機制單元測試和集成測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""LLM 故障轉移機制的單元測試和集成測試。"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch
from typing import Any, Dict

import pytest

from agents.task_analyzer.models import LLMProvider
from llm.clients.base import BaseLLMClient
from llm.failover import (
    HealthCheckResult,
    LLMFailoverManager,
    RetryConfig,
)


# Mock LLM Client
class MockLLMClient(BaseLLMClient):
    """模擬 LLM 客戶端用於測試。"""

    def __init__(
        self,
        available: bool = True,
        should_fail: bool = False,
        should_timeout: bool = False,
        delay: float = 0.0,
    ):
        self.available = available
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.delay = delay

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def default_model(self) -> str:
        return "mock-model"

    def is_available(self) -> bool:
        return self.available

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.should_timeout:
            await asyncio.sleep(10)  # 模擬超時

        if self.should_fail:
            raise Exception("Mock client failure")

        return {"text": "test response", "model": model or self.default_model}

    async def chat(
        self,
        messages: list[Dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        if self.should_fail:
            raise Exception("Mock client failure")
        return {"content": "test response", "model": model or self.default_model}

    async def embeddings(
        self,
        text: str,
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> list[float]:
        if self.should_fail:
            raise Exception("Mock client failure")
        return [0.1, 0.2, 0.3]


@pytest.fixture
def failover_manager() -> LLMFailoverManager:
    """創建故障轉移管理器實例。"""
    return LLMFailoverManager(
        health_check_interval=1.0,
        health_check_timeout=2.0,
        failure_threshold=3,
    )


@pytest.fixture
def retry_config() -> RetryConfig:
    """創建重試配置。"""
    return RetryConfig(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        exponential_base=2.0,
        jitter=True,
    )


class TestHealthCheckResult:
    """測試 HealthCheckResult 數據類。"""

    def test_health_check_result_creation(self):
        """測試健康檢查結果創建。"""
        result = HealthCheckResult(
            provider=LLMProvider.CHATGPT,
            healthy=True,
            latency=0.5,
        )
        assert result.provider == LLMProvider.CHATGPT
        assert result.healthy is True
        assert result.latency == 0.5
        assert result.error is None
        assert result.timestamp > 0

    def test_health_check_result_with_error(self):
        """測試帶錯誤的健康檢查結果。"""
        result = HealthCheckResult(
            provider=LLMProvider.GEMINI,
            healthy=False,
            latency=1.0,
            error="Test error",
        )
        assert result.healthy is False
        assert result.error == "Test error"


class TestLLMFailoverManager:
    """測試 LLMFailoverManager 類。"""

    @pytest.mark.asyncio
    async def test_check_provider_health_success(
        self, failover_manager: LLMFailoverManager
    ):
        """測試成功的健康檢查。"""
        mock_client = MockLLMClient(available=True, should_fail=False)

        result = await failover_manager.check_provider_health(
            LLMProvider.CHATGPT, client=mock_client
        )

        assert result.provider == LLMProvider.CHATGPT
        assert result.healthy is True
        assert result.latency >= 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_check_provider_health_client_not_available(
        self, failover_manager: LLMFailoverManager
    ):
        """測試客戶端不可用的健康檢查。"""
        mock_client = MockLLMClient(available=False)

        result = await failover_manager.check_provider_health(
            LLMProvider.CHATGPT, client=mock_client
        )

        assert result.healthy is False
        assert result.error == "Client not available"

    @pytest.mark.asyncio
    async def test_check_provider_health_timeout(
        self, failover_manager: LLMFailoverManager
    ):
        """測試健康檢查超時。"""
        failover_manager.health_check_timeout = 0.1
        mock_client = MockLLMClient(available=True, should_timeout=True)

        result = await failover_manager.check_provider_health(
            LLMProvider.CHATGPT, client=mock_client
        )

        assert result.healthy is False
        assert result.error == "Health check timeout"

    @pytest.mark.asyncio
    async def test_check_provider_health_failure(
        self, failover_manager: LLMFailoverManager
    ):
        """測試健康檢查失敗。"""
        mock_client = MockLLMClient(available=True, should_fail=True)

        result = await failover_manager.check_provider_health(
            LLMProvider.CHATGPT, client=mock_client
        )

        assert result.healthy is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_check_all_providers(self, failover_manager: LLMFailoverManager):
        """測試檢查所有提供商。"""
        with patch("llm.failover.LLMClientFactory.create_client") as mock_create:
            mock_create.return_value = MockLLMClient(available=True)

            providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
            results = await failover_manager.check_all_providers(providers)

            assert len(results) == 2
            assert LLMProvider.CHATGPT in results
            assert LLMProvider.GEMINI in results

    def test_is_provider_healthy_unknown(self, failover_manager: LLMFailoverManager):
        """測試未知提供商的健康狀態（應視為健康）。"""
        # 未檢查過的提供商應視為健康
        assert failover_manager.is_provider_healthy(LLMProvider.CHATGPT) is True

    def test_is_provider_healthy_success(self, failover_manager: LLMFailoverManager):
        """測試健康的提供商。"""
        # 設置健康的檢查結果
        failover_manager._provider_health[LLMProvider.CHATGPT] = HealthCheckResult(
            provider=LLMProvider.CHATGPT,
            healthy=True,
            latency=0.5,
        )
        failover_manager._failure_counts[LLMProvider.CHATGPT] = 0
        failover_manager._last_health_check[LLMProvider.CHATGPT] = time.time()

        assert failover_manager.is_provider_healthy(LLMProvider.CHATGPT) is True

    def test_is_provider_healthy_failure_threshold(
        self, failover_manager: LLMFailoverManager
    ):
        """測試超過失敗閾值的提供商。"""
        # 設置失敗的檢查結果，並超過失敗閾值
        failover_manager._provider_health[LLMProvider.CHATGPT] = HealthCheckResult(
            provider=LLMProvider.CHATGPT,
            healthy=False,
            latency=0.5,
            error="Test error",
        )
        failover_manager._failure_counts[LLMProvider.CHATGPT] = 3  # 等於閾值
        failover_manager._last_health_check[LLMProvider.CHATGPT] = time.time()

        assert failover_manager.is_provider_healthy(LLMProvider.CHATGPT) is False

    def test_is_provider_healthy_expired(self, failover_manager: LLMFailoverManager):
        """測試過期的健康檢查結果。"""
        # 設置過期的檢查結果（超過2倍間隔）
        failover_manager._provider_health[LLMProvider.CHATGPT] = HealthCheckResult(
            provider=LLMProvider.CHATGPT,
            healthy=False,
            latency=0.5,
            error="Test error",
        )
        failover_manager._failure_counts[LLMProvider.CHATGPT] = 1
        # 設置為很久以前的時間（超過2倍間隔）
        failover_manager._last_health_check[LLMProvider.CHATGPT] = (
            time.time() - failover_manager.health_check_interval * 3
        )

        # 過期應視為健康（避免誤判）
        assert failover_manager.is_provider_healthy(LLMProvider.CHATGPT) is True

    def test_get_healthy_providers(self, failover_manager: LLMFailoverManager):
        """測試獲取健康的提供商列表。"""
        # 設置兩個提供商：一個健康，一個不健康
        failover_manager._provider_health[LLMProvider.CHATGPT] = HealthCheckResult(
            provider=LLMProvider.CHATGPT,
            healthy=True,
            latency=0.5,
        )
        failover_manager._failure_counts[LLMProvider.CHATGPT] = 0
        failover_manager._last_health_check[LLMProvider.CHATGPT] = time.time()

        failover_manager._provider_health[LLMProvider.GEMINI] = HealthCheckResult(
            provider=LLMProvider.GEMINI,
            healthy=False,
            latency=0.5,
            error="Test error",
        )
        failover_manager._failure_counts[LLMProvider.GEMINI] = 3
        failover_manager._last_health_check[LLMProvider.GEMINI] = time.time()

        healthy = failover_manager.get_healthy_providers(
            [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        )

        assert LLMProvider.CHATGPT in healthy
        assert LLMProvider.GEMINI not in healthy

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(
        self, failover_manager: LLMFailoverManager
    ):
        """測試重試成功場景。"""
        call_count = 0

        async def mock_func(provider: LLMProvider) -> str:
            nonlocal call_count
            call_count += 1
            return f"success-{provider.value}"

        result = await failover_manager.execute_with_retry(
            mock_func, LLMProvider.CHATGPT
        )

        assert result == "success-chatgpt"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_with_retry_retry_success(
        self, failover_manager: LLMFailoverManager, retry_config: RetryConfig
    ):
        """測試重試後成功場景。"""
        failover_manager.retry_config = retry_config
        call_count = 0

        async def mock_func(provider: LLMProvider) -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return f"success-{provider.value}"

        result = await failover_manager.execute_with_retry(
            mock_func, LLMProvider.CHATGPT
        )

        assert result == "success-chatgpt"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_failover_success(
        self, failover_manager: LLMFailoverManager, retry_config: RetryConfig
    ):
        """測試故障轉移成功場景。"""
        failover_manager.retry_config = retry_config
        call_count = 0

        async def mock_func(provider: LLMProvider) -> str:
            nonlocal call_count
            call_count += 1
            if provider == LLMProvider.CHATGPT:
                raise Exception("Primary provider failed")
            return f"success-{provider.value}"

        # 設置備用提供商為健康
        failover_manager._provider_health[LLMProvider.GEMINI] = HealthCheckResult(
            provider=LLMProvider.GEMINI,
            healthy=True,
            latency=0.5,
        )
        failover_manager._failure_counts[LLMProvider.GEMINI] = 0
        failover_manager._last_health_check[LLMProvider.GEMINI] = time.time()

        result = await failover_manager.execute_with_retry(
            mock_func,
            LLMProvider.CHATGPT,
            fallback_providers=[LLMProvider.GEMINI],
        )

        assert result == "success-gemini"
        assert call_count >= 2  # 至少重試一次主提供商，然後故障轉移

    @pytest.mark.asyncio
    async def test_execute_with_retry_all_failed(
        self, failover_manager: LLMFailoverManager, retry_config: RetryConfig
    ):
        """測試所有重試和故障轉移都失敗的場景。"""
        failover_manager.retry_config = retry_config

        async def mock_func(provider: LLMProvider) -> str:
            raise Exception(f"Provider {provider.value} failed")

        with pytest.raises(Exception, match="Provider"):
            await failover_manager.execute_with_retry(
                mock_func,
                LLMProvider.CHATGPT,
                fallback_providers=[LLMProvider.GEMINI],
            )

    @pytest.mark.asyncio
    async def test_execute_with_retry_exponential_backoff(
        self, failover_manager: LLMFailoverManager
    ):
        """測試指數退避機制。"""
        retry_config = RetryConfig(
            max_retries=3,
            initial_delay=0.1,
            max_delay=1.0,
            exponential_base=2.0,
            jitter=False,  # 關閉 jitter 以便測試
        )
        failover_manager.retry_config = retry_config

        call_times: list[float] = []
        call_count = 0

        async def mock_func(provider: LLMProvider) -> str:
            nonlocal call_count
            call_count += 1
            call_times.append(time.time())
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"

        result = await failover_manager.execute_with_retry(
            mock_func, LLMProvider.CHATGPT
        )

        assert result == "success"
        assert call_count == 3

        # 驗證延遲時間（允許一些誤差）
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            # 第一次重試延遲應該是 initial_delay * (2^0) = 0.1
            assert 0.09 <= delay1 <= 0.15

        if len(call_times) >= 3:
            delay2 = call_times[2] - call_times[1]
            # 第二次重試延遲應該是 initial_delay * (2^1) = 0.2
            assert 0.19 <= delay2 <= 0.25

    def test_get_provider_health_status(self, failover_manager: LLMFailoverManager):
        """測試獲取提供商健康狀態。"""
        # 設置一些提供商的健康狀態
        failover_manager._provider_health[LLMProvider.CHATGPT] = HealthCheckResult(
            provider=LLMProvider.CHATGPT,
            healthy=True,
            latency=0.5,
        )
        failover_manager._failure_counts[LLMProvider.CHATGPT] = 0
        failover_manager._last_health_check[LLMProvider.CHATGPT] = time.time()

        status = failover_manager.get_provider_health_status()

        assert LLMProvider.CHATGPT in status
        assert status[LLMProvider.CHATGPT]["healthy"] is True
        assert status[LLMProvider.CHATGPT]["failure_count"] == 0
        assert status[LLMProvider.CHATGPT]["latency"] == 0.5

    @pytest.mark.asyncio
    async def test_start_stop(self, failover_manager: LLMFailoverManager):
        """測試啟動和停止健康檢查任務。"""
        await failover_manager.start()
        assert failover_manager._running is True

        # 等待一小段時間確保任務啟動
        await asyncio.sleep(0.1)

        await failover_manager.stop()
        assert failover_manager._running is False


# 集成測試：測試與 MoE Manager 的集成
class TestFailoverIntegration:
    """測試故障轉移與 MoE Manager 的集成。"""

    @pytest.mark.asyncio
    async def test_failover_integration_with_moe_manager(self):
        """測試故障轉移與 MoE Manager 的集成。"""
        from llm.moe_manager import LLMMoEManager
        from llm.failover import LLMFailoverManager

        # 創建故障轉移管理器
        failover_manager = LLMFailoverManager(
            health_check_interval=1.0,
            health_check_timeout=2.0,
            failure_threshold=3,
        )

        # 創建 MoE Manager 並啟用故障轉移
        moe_manager = LLMMoEManager(
            enable_failover=True,
            failover_manager=failover_manager,
        )

        # 驗證故障轉移管理器已正確集成
        assert moe_manager.failover_manager is not None
        assert moe_manager.enable_failover is True

    @pytest.mark.asyncio
    async def test_failover_generate_with_healthy_providers(self):
        """測試使用健康提供商的故障轉移生成。"""
        failover_manager = LLMFailoverManager(
            health_check_interval=1.0,
            health_check_timeout=2.0,
            failure_threshold=3,
        )

        # 設置一個提供商為健康
        failover_manager._provider_health[LLMProvider.GEMINI] = HealthCheckResult(
            provider=LLMProvider.GEMINI,
            healthy=True,
            latency=0.5,
        )
        failover_manager._failure_counts[LLMProvider.GEMINI] = 0
        failover_manager._last_health_check[LLMProvider.GEMINI] = time.time()

        # 驗證故障轉移會優先選擇健康的提供商
        healthy = failover_manager.get_healthy_providers()
        assert LLMProvider.GEMINI in healthy
        # 驗證故障轉移會優先選擇健康的提供商
        healthy = failover_manager.get_healthy_providers()
        assert LLMProvider.GEMINI in healthy
