# 代碼功能說明: LLM 集成測試
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""LLM 系統集成測試，測試端到端流程。"""

from unittest.mock import AsyncMock, patch
import pytest

from agents.task_analyzer.models import LLMProvider, TaskClassificationResult, TaskType
from llm.load_balancer import MultiLLMLoadBalancer
from llm.moe_manager import LLMMoEManager


class TestLLMIntegration:
    """LLM 系統集成測試類。"""

    @pytest.fixture
    def mock_clients(self):
        """創建多個模擬客戶端。"""
        clients = {}
        for provider in [LLMProvider.CHATGPT, LLMProvider.GEMINI, LLMProvider.QWEN]:
            client = AsyncMock()
            client.provider_name = provider.value
            client.default_model = f"{provider.value}-model"
            client.is_available.return_value = True
            client.generate = AsyncMock(
                return_value={
                    "text": f"Response from {provider.value}",
                    "content": f"Response from {provider.value}",
                }
            )
            client.chat = AsyncMock(
                return_value={
                    "content": f"Chat response from {provider.value}",
                    "message": f"Chat response from {provider.value}",
                }
            )
            clients[provider] = client
        return clients

    @pytest.mark.asyncio
    async def test_end_to_end_generate(self, mock_clients):
        """測試端到端生成流程。"""
        manager = LLMMoEManager(enable_failover=True)

        def create_client_side_effect(provider, **kwargs):
            return mock_clients.get(provider)

        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            side_effect=create_client_side_effect,
        ):
            task_classification = TaskClassificationResult(
                task_type=TaskType.QUERY,
                confidence=0.9,
                reasoning="Test",
            )

            result = await manager.generate(
                "Test prompt",
                task_classification=task_classification,
            )

            assert "text" in result or "content" in result

    @pytest.mark.asyncio
    async def test_multi_llm_switching(self, mock_clients):
        """測試多 LLM 切換。"""
        manager = LLMMoEManager(enable_failover=True)

        def create_client_side_effect(provider, **kwargs):
            return mock_clients.get(provider)

        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            side_effect=create_client_side_effect,
        ):
            providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI, LLMProvider.QWEN]

            for provider in providers:
                result = await manager.generate(
                    "Test prompt",
                    provider=provider,
                )
                assert "text" in result or "content" in result
                assert mock_clients[provider].generate.called

    @pytest.mark.asyncio
    async def test_failover_scenario(self, mock_clients):
        """測試故障轉移場景。"""
        manager = LLMMoEManager(enable_failover=True)

        failing_client = mock_clients[LLMProvider.CHATGPT]
        failing_client.generate = AsyncMock(side_effect=Exception("Primary failed"))

        fallback_client = mock_clients[LLMProvider.GEMINI]

        def create_client_side_effect(provider, **kwargs):
            if provider == LLMProvider.CHATGPT:
                return failing_client
            return mock_clients.get(provider)

        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            side_effect=create_client_side_effect,
        ):
            task_classification = TaskClassificationResult(
                task_type=TaskType.QUERY,
                confidence=0.9,
                reasoning="Test",
            )

            result = await manager.generate(
                "Test prompt",
                task_classification=task_classification,
            )

            assert "text" in result or "content" in result
            assert fallback_client.generate.called

    def test_load_balancer_integration(self):
        """測試負載均衡器集成。"""
        providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        balancer = MultiLLMLoadBalancer(providers, strategy="round_robin")
        selected_provider = balancer.select_provider()
        assert selected_provider in providers
        balancer.mark_success(selected_provider)
        stats = balancer.get_provider_stats()
        assert selected_provider in stats
