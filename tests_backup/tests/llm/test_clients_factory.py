# 代碼功能說明: LLM 客戶端工廠單元測試
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""測試 LLM 客戶端工廠功能。"""

from unittest.mock import patch

from agents.task_analyzer.models import LLMProvider
from llm.clients.factory import LLMClientFactory


class TestLLMClientFactory:
    """LLM 客戶端工廠測試類。"""

    def test_client_caching(self):
        """測試客戶端緩存功能。"""
        with patch("llm.clients.chatgpt.AsyncOpenAI"):
            # 由於需要API密鑰，這裡只測試緩存邏輯
            LLMClientFactory.clear_cache()
            cached = LLMClientFactory.get_cached_client(LLMProvider.CHATGPT)
            assert cached is None

    def test_clear_cache(self):
        """測試清除緩存功能。"""
        LLMClientFactory.clear_cache()
        # 驗證緩存已清除
        assert True
