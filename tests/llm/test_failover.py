# 代碼功能說明: LLM 故障轉移機制單元測試
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""測試 LLM 故障轉移機制功能。"""


from agents.task_analyzer.models import LLMProvider
from llm.failover import LLMFailoverManager


class TestLLMFailoverManager:
    """LLM 故障轉移管理器測試類。"""

    def test_is_provider_healthy(self):
        """測試檢查提供商是否健康。"""
        manager = LLMFailoverManager()
        assert manager.is_provider_healthy(LLMProvider.CHATGPT) is True

    def test_get_healthy_providers(self):
        """測試獲取健康的提供商列表。"""
        manager = LLMFailoverManager()
        providers = [LLMProvider.CHATGPT, LLMProvider.GEMINI]
        healthy = manager.get_healthy_providers(providers)
        assert len(healthy) == 2
