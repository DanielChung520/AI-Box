# 代碼功能說明: 多 LLM 負載均衡器單元測試
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""測試多 LLM 負載均衡器功能。"""


from agents.task_analyzer.models import LLMProvider
from llm.load_balancer import MultiLLMLoadBalancer


class TestMultiLLMLoadBalancer:
    """多 LLM 負載均衡器測試類。"""

    def test_init(self):
        """測試初始化。"""
        providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        balancer = MultiLLMLoadBalancer(providers)
        assert balancer.strategy == "round_robin"
        assert len(balancer._provider_nodes) == 2

    def test_select_provider_round_robin(self):
        """測試輪詢策略。"""
        providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        balancer = MultiLLMLoadBalancer(providers, strategy="round_robin")
        provider = balancer.select_provider()
        assert provider in providers

    def test_mark_success(self):
        """測試標記成功。"""
        providers = [LLMProvider.CHATGPT]
        balancer = MultiLLMLoadBalancer(providers)
        balancer.mark_failure(LLMProvider.CHATGPT)
        assert not balancer._provider_nodes[LLMProvider.CHATGPT].healthy
        balancer.mark_success(LLMProvider.CHATGPT)
        assert balancer._provider_nodes[LLMProvider.CHATGPT].healthy
