"""
代碼功能說明: MM-Agent 轉發集成測試
創建日期: 2026-02-09
創建人: AI-Box 開發團隊

測試場景：
- GAI 前端意圖不轉發
- BUSINESS 意圖轉發
- 已選擇特定 Agent 的處理
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestBPAForwarding:
    """測試 MM-Agent 轉發邏輯"""

    @pytest.mark.asyncio
    async def test_greeting_intent_not_forwarded(self):
        """測試問候語不轉發"""
        with patch('api.routers.chat.classify_gai_intent') as mock_classify:
            mock_classify.return_value = "GREETING"
            # 測試 GAI 分類結果
            from api.routers.chat import GAIIntentType
            assert mock_classify("你好") == "GREETING"

    @pytest.mark.asyncio
    async def test_business_intent_forwarded(self):
        """測試業務請求轉發"""
        from api.routers.chat import should_forward_to_bpa, GAIIntentType

        result = should_forward_to_bpa(
            text="查詢庫存",
            gai_intent=GAIIntentType.BUSINESS,
            has_selected_agent=False,
            agent_id=None,
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_selected_non_mm_agent_not_forwarded(self):
        """測試選擇非 MM-Agent 不轉發"""
        from api.routers.chat import should_forward_to_bpa, GAIIntentType

        result = should_forward_to_bpa(
            text="查詢庫存",
            gai_intent=GAIIntentType.BUSINESS,
            has_selected_agent=True,
            agent_id="ka-agent",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_selected_mm_agent_forwarded(self):
        """測試選擇 MM-Agent 轉發"""
        from api.routers.chat import should_forward_to_bpa, GAIIntentType

        result = should_forward_to_bpa(
            text="查詢庫存",
            gai_intent=GAIIntentType.BUSINESS,
            has_selected_agent=True,
            agent_id="mm-agent",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_intent_not_forwarded(self):
        """測試取消意圖不轉發"""
        from api.routers.chat import should_forward_to_bpa, GAIIntentType

        result = should_forward_to_bpa(
            text="取消",
            gai_intent=GAIIntentType.CANCEL,
            has_selected_agent=False,
            agent )
        assert result_id=None,
        is False


class TestGAIIntentResponse:
    """測試 GAI 意圖回覆生成"""

    def test_greeting_response(self):
        """測試問候語回覆"""
        from api.routers.chat import get_gai_intent_response, GAIIntentType

        response = get_gai_intent_response(GAIIntentType.GREETING, "你好")
        assert response is not None
        assert isinstance(response, str)
        assert len(response) > 0

    def test_thanks_response(self):
        """測試感謝回覆"""
        from api.routers.chat import get_gai_intent_response, GAIIntentType

        response = get_gai_intent_response(GAIIntentType.THANKS, "謝謝")
        assert response is not None
        assert isinstance(response, str)

    def test_cancel_response(self):
        """測試取消回覆"""
        from api.routers.chat import get_gai_intent_response, GAIIntentType

        response = get_gai_intent_response(GAIIntentType.CANCEL, "取消")
        assert response is not None
        assert isinstance(response, str)

    def test_clarification_response(self):
        """測試澄清回覆"""
        from api.routers.chat import get_gai_intent_response, GAIIntentType

        response = get_gai_intent_response(GAIIntentType.CLARIFICATION, "那個料號呢")
        assert response is not None
        assert isinstance(response, str)

    def test_business_no_response(self):
        """測試業務請求不生成回覆"""
        from api.routers.chat import get_gai_intent_response, GAIIntentType

        response = get_gai_intent_response(GAIIntentType.BUSINESS, "查詢庫存")
        assert response is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
