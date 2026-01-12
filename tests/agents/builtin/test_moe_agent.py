# 代碼功能說明: MoE Agent 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""MoE Agent 單元測試

測試 MoE Agent 的核心功能：文本生成、對話生成、嵌入向量生成和路由指標查詢。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.builtin.moe_agent.agent import MoEAgent
from agents.services.protocol.base import AgentServiceRequest, AgentServiceStatus


class TestMoEAgent:
    """MoE Agent 測試類"""

    @pytest.fixture
    def moe_agent(self):
        """創建 MoEAgent 實例"""
        with patch("agents.builtin.moe_agent.agent.LLMMoEManager") as mock_moe:
            mock_manager = MagicMock()
            mock_moe.return_value = mock_manager
            return MoEAgent(moe_manager=mock_manager)

    @pytest.fixture
    def sample_request(self):
        """創建示例請求"""
        return AgentServiceRequest(
            task_id="test-task-001",
            task_type="moe",
            task_data={
                "action": "generate",
                "prompt": "測試提示詞",
            },
        )

    @pytest.mark.asyncio
    async def test_execute_generate(self, moe_agent, sample_request):
        """測試執行文本生成"""
        # Mock MoE Manager 的 generate 方法
        moe_agent._moe_manager.generate = AsyncMock(return_value={"text": "生成的文本"})

        response = await moe_agent.execute(sample_request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "generate"
        assert "result" in response.result

    @pytest.mark.asyncio
    async def test_execute_chat(self, moe_agent):
        """測試執行對話生成"""
        request = AgentServiceRequest(
            task_id="test-task-002",
            task_type="moe",
            task_data={
                "action": "chat",
                "messages": [{"role": "user", "content": "你好"}],
            },
        )

        # Mock MoE Manager 的 chat 方法
        moe_agent._moe_manager.chat = AsyncMock(return_value={"content": "你好！"})

        response = await moe_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "chat"

    @pytest.mark.asyncio
    async def test_execute_embeddings(self, moe_agent):
        """測試執行嵌入向量生成"""
        request = AgentServiceRequest(
            task_id="test-task-003",
            task_type="moe",
            task_data={
                "action": "embeddings",
                "text": "測試文本",
            },
        )

        # Mock MoE Manager 的 embeddings 方法
        moe_agent._moe_manager.embeddings = AsyncMock(return_value=[0.1, 0.2, 0.3])

        response = await moe_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "embeddings"
        assert "embeddings" in response.result["result"]

    @pytest.mark.asyncio
    async def test_execute_get_metrics(self, moe_agent):
        """測試獲取路由指標"""
        request = AgentServiceRequest(
            task_id="test-task-004",
            task_type="moe",
            task_data={"action": "get_metrics"},
        )

        # Mock MoE Manager 的 get_routing_metrics 方法
        moe_agent._moe_manager.get_routing_metrics = MagicMock(
            return_value={
                "provider_metrics": {},
                "strategy_metrics": {},
                "recommendations": [],
            }
        )

        response = await moe_agent.execute(request)

        assert response.status == "completed"
        assert response.result["success"] is True
        assert response.result["action"] == "get_metrics"

    @pytest.mark.asyncio
    async def test_execute_unknown_action(self, moe_agent):
        """測試未知操作"""
        request = AgentServiceRequest(
            task_id="test-task-005",
            task_type="moe",
            task_data={"action": "unknown_action"},
        )

        response = await moe_agent.execute(request)

        assert response.status == "failed"
        assert response.result["success"] is False
        assert "Unknown action" in response.result["error"]

    @pytest.mark.asyncio
    async def test_execute_missing_prompt(self, moe_agent):
        """測試缺少必要參數"""
        request = AgentServiceRequest(
            task_id="test-task-006",
            task_type="moe",
            task_data={"action": "generate"},
        )

        response = await moe_agent.execute(request)

        assert response.status == "failed"
        assert response.result["success"] is False
        assert "prompt is required" in response.result["error"]

    @pytest.mark.asyncio
    async def test_health_check(self, moe_agent):
        """測試健康檢查"""
        # Mock get_routing_metrics
        moe_agent._moe_manager.get_routing_metrics = MagicMock(return_value={})

        status = await moe_agent.health_check()
        assert status == AgentServiceStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_get_capabilities(self, moe_agent):
        """測試獲取服務能力"""
        capabilities = await moe_agent.get_capabilities()

        assert capabilities["agent_id"] == "moe_agent"
        assert capabilities["agent_type"] == "dedicated_service"
        assert "generate" in capabilities["capabilities"]
        assert "chat" in capabilities["capabilities"]
        assert "embeddings" in capabilities["capabilities"]

    @pytest.mark.asyncio
    async def test_stream_chat(self, moe_agent):
        """測試流式對話生成"""

        # Mock MoE Manager 的 chat_stream 方法
        async def mock_stream():
            yield "Hello"
            yield " World"

        moe_agent._moe_manager.chat_stream = mock_stream

        chunks = []
        async for chunk in moe_agent.stream_chat(messages=[{"role": "user", "content": "你好"}]):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Hello"
        assert chunks[1] == " World"
