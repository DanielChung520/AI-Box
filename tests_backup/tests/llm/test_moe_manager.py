# 代碼功能說明: LLM MoE 管理器單元測試
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""測試 LLM MoE 管理器功能。"""

from unittest.mock import AsyncMock, patch
import pytest

from agents.task_analyzer.models import LLMProvider
from llm.moe_manager import LLMMoEManager


class TestLLMMoEManager:
    """LLM MoE 管理器測試類。"""

    @pytest.fixture
    def manager(self):
        """創建 MoE 管理器實例。"""
        return LLMMoEManager(enable_failover=False)

    @pytest.fixture
    def mock_client(self):
        """創建模擬客戶端。"""
        client = AsyncMock()
        client.provider_name = "chatgpt"
        client.default_model = "gpt-4"
        client.is_available.return_value = True
        client.generate = AsyncMock(
            return_value={"text": "Test response", "content": "Test response"}
        )
        client.chat = AsyncMock(
            return_value={
                "content": "Test chat response",
                "message": "Test chat response",
            }
        )
        client.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])
        return client

    @pytest.mark.asyncio
    async def test_generate_with_provider(self, manager, mock_client):
        """測試使用指定提供商生成文本。"""
        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            return_value=mock_client,
        ):
            result = await manager.generate(
                "Test prompt",
                provider=LLMProvider.CHATGPT,
            )
            assert "text" in result or "content" in result
            mock_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_with_provider(self, manager, mock_client):
        """測試使用指定提供商進行對話。"""
        messages = [{"role": "user", "content": "Hello"}]
        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            return_value=mock_client,
        ):
            result = await manager.chat(
                messages,
                provider=LLMProvider.CHATGPT,
            )
            assert "content" in result or "message" in result
            mock_client.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_embeddings(self, manager, mock_client):
        """測試生成嵌入向量。"""
        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            return_value=mock_client,
        ):
            result = await manager.embeddings("Test text", provider=LLMProvider.CHATGPT)
            assert isinstance(result, list)
            assert len(result) > 0

    def test_get_routing_metrics(self, manager):
        """測試獲取路由指標。"""
        metrics = manager.get_routing_metrics()
        assert "provider_metrics" in metrics
        assert "strategy_metrics" in metrics
        assert "recommendations" in metrics

    def test_get_client(self, manager, mock_client):
        """測試獲取客戶端。"""
        with patch(
            "llm.moe_manager.LLMClientFactory.create_client",
            return_value=mock_client,
        ):
            client = manager.get_client(LLMProvider.CHATGPT)
            assert client is not None
            assert client.provider_name == "chatgpt"
