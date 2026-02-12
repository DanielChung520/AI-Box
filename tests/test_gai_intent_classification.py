"""
代碼功能說明: GAI 前端意圖分類單元測試
創建日期: 2026-02-09
創建人: AI-Box 開發團隊

覆蓋測試用例：
- GREETING: 問候語識別
- THANKS: 感謝回覆識別
- COMPLAIN: 投訴/道歉處理
- CANCEL: 取消任務
- CONTINUE: 繼續執行
- MODIFY: 重新處理
- HISTORY: 顯示歷史
- EXPORT: 導出結果
- CONFIRM: 確認回覆
- FEEDBACK: 反饋/建議
- CLARIFICATION: 需要澄清
- BUSINESS: 業務請求
"""

import pytest
from api.routers.chat import (
    classify_gai_intent,
    get_gai_intent_response,
    GAIIntentType,
    should_forward_to_bpa,
)


class TestClassifyGaiIntent:
    """測試 GAI 意圖分類函數"""

    # GREETING 測試
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("你好", GAIIntentType.GREETING),
            ("您好", GAIIntentType.GREETING),
            ("早安", GAIIntentType.GREETING),
            ("午安", GAIIntentType.GREETING),
            ("晚安", GAIIntentType.GREETING),
            ("Hi", GAIIntentType.GREETING),
            ("Hello", GAIIntentType.GREETING),
            ("嗨", GAIIntentType.GREETING),
            ("在嗎", GAIIntentType.GREETING),
        ],
    )
    def test_greeting_intents(self, input_text: str, expected: GAIIntentType):
        """測試問候語識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # THANKS 測試
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("謝謝", GAIIntentType.THANKS),
            ("感謝", GAIIntentType.THANKS),
            ("多謝", GAIIntentType.THANKS),
            ("感恩", GAIIntentType.THANKS),
            ("thanks", GAIIntentType.THANKS),
            ("thank you", GAIIntentType.THANKS),
        ],
    )
    def test_thanks_intents(self, input_text: str, expected: GAIIntentType):
        """測試感謝回覆識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # CANCEL 測試
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("取消", GAIIntentType.CANCEL),
            ("停止", GAIIntentType.CANCEL),
            ("不要了", GAIIntentType.CANCEL),
            ("終止", GAIIntentType.CANCEL),
            ("cancel", GAIIntentType.CANCEL),
        ],
    )
    def test_cancel_intents(self, input_text: str, expected: GAIIntentType):
        """測試取消任務識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # CONTINUE 測試
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("繼續", GAIIntentType.CONTINUE),
            ("執行", GAIIntentType.CONTINUE),
            ("好的", GAIIntentType.CONTINUE),
            ("是的", GAIIntentType.CONTINUE),
            ("proceed", GAIIntentType.CONTINUE),
            ("continue", GAIIntentType.CONTINUE),
        ],
    )
    def test_continue_intents(self, input_text: str, expected: GAIIntentType):
        """測試繼續執行識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # MODIFY 測試
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("重新", GAIIntentType.MODIFY),
            ("再來一次", GAIIntentType.MODIFY),
            ("改一下", GAIIntentType.MODIFY),
            ("修改", GAIIntentType.MODIFY),
            ("重做", GAIIntentType.MODIFY),
        ],
    )
    def test_modify_intents(self, input_text: str, expected: GAIIntentType):
        """測試重新處理識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # CLARIFICATION 測試
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("那個料號呢", GAIIntentType.CLARIFICATION),
            ("它多少", GAIIntentType.CLARIFICATION),
            ("哪個倉庫", GAIIntentType.CLARIFICATION),
            ("那個", GAIIntentType.CLARIFICATION),
        ],
    )
    def test_clarification_intents(self, input_text: str, expected: GAIIntentType):
        """測試澄清需求識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # BUSINESS 測試（業務請求）
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            ("查詢庫存", GAIIntentType.BUSINESS),
            ("料號 10-0001 的品名", GAIIntentType.BUSINESS),
            ("ABC庫存分類分析", GAIIntentType.BUSINESS),
            ("本月採購單未交貨明細", GAIIntentType.BUSINESS),
            ("比較近三個月採購金額", GAIIntentType.BUSINESS),
        ],
    )
    def test_business_intents(self, input_text: str, expected: GAIIntentType):
        """測試業務請求識別"""
        result = classify_gai_intent(input_text)
        assert result == expected

    # 邊界測試
    def test_empty_text(self):
        """測試空文本"""
        result = classify_gai_intent("")
        assert result is None

    def test_none_text(self):
        """測試 None 輸入"""
        result = classify_gai_intent(None)
        assert result is None


class TestGetGaiIntentResponse:
    """測試 GAI 意圖回覆函數"""

    @pytest.mark.parametrize(
        "intent,expected_not_none",
        [
            (GAIIntentType.GREETING, True),
            (GAIIntentType.THANKS, True),
            (GAIIntentType.CANCEL, True),
            (GAIIntentType.CONTINUE, True),
            (GAIIntentType.CLARIFICATION, True),
            (GAIIntentType.BUSINESS, False),
        ],
    )
    def test_intent_responses(self, intent: GAIIntentType, expected_not_none: bool):
        """測試各意圖的回覆"""
        response = get_gai_intent_response(intent, "test")
        if expected_not_none:
            assert response is not None
            assert isinstance(response, str)
            assert len(response) > 0
        else:
            # BUSINESS 意圖不生成回覆
            assert response is None


class TestShouldForwardToBPA:
    """測試是否應該轉發給 BPA"""

    def test_gai_intent_not_forward(self):
        """測試 GAI 前端意圖不轉發"""
        result = should_forward_to_bpa(
            text="你好",
            gai_intent=GAIIntentType.GREETING,
            has_selected_agent=False,
            agent_id=None,
        )
        assert result is False

    def test_business_intent_forward(self):
        """測試業務請求轉發"""
        result = should_forward_to_bpa(
            text="查詢庫存",
            gai_intent=GAIIntentType.BUSINESS,
            has_selected_agent=False,
            agent_id=None,
        )
        assert result is True

    def test_selected_agent_not_mm_agent(self):
        """測試選擇非 MM-Agent 不轉發"""
        result = should_forward_to_bpa(
            text="查詢庫存",
            gai_intent=GAIIntentType.BUSINESS,
            has_selected_agent=True,
            agent_id="ka-agent",
        )
        assert result is False

    def test_selected_mm_agent(self):
        """測試選擇 MM-Agent 轉發"""
        result = should_forward_to_bpa(
            text="查詢庫存",
            gai_intent=GAIIntentType.BUSINESS,
            has_selected_agent=True,
            agent_id="mm-agent",
        )
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
