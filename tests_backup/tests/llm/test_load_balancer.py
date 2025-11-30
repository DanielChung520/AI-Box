# 代碼功能說明: 負載均衡器單元測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""負載均衡器單元測試和集成測試。"""

from __future__ import annotations

import time


from agents.task_analyzer.models import LLMProvider
from llm.load_balancer import LLMProviderNode, MultiLLMLoadBalancer


class TestLLMProviderNode:
    """測試 LLMProviderNode 類。"""

    def test_available_healthy(self):
        """測試健康節點可用性。"""
        node = LLMProviderNode(provider=LLMProvider.CHATGPT, healthy=True)
        assert node.available(time.time()) is True


class TestMultiLLMLoadBalancer:
    """測試 MultiLLMLoadBalancer 類。"""

    def test_init_with_providers(self):
        """測試初始化。"""
        providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        lb = MultiLLMLoadBalancer(providers=providers)
        assert len(lb._provider_nodes) == 2

    def test_round_robin_strategy(self):
        """測試輪詢策略。"""
        providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        lb = MultiLLMLoadBalancer(providers=providers, strategy="round_robin")
        selected = [lb.select_provider() for _ in range(4)]
        assert selected[0] == LLMProvider.CHATGPT
        assert selected[1] == LLMProvider.GEMINI
        assert selected[2] == LLMProvider.CHATGPT
        assert selected[3] == LLMProvider.GEMINI
