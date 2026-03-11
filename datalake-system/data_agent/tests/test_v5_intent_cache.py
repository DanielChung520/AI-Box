# -*- coding: utf-8 -*-
# 代碼功能說明: CachedIntentMatcher (v5_intent_cache) 單元測試 — thin wrapper 驗證
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11
"""
CachedIntentMatcher 單元測試

測試覆蓋：
1. match_intent 委派給 DA_IntentRAG
2. DA_IntentRAG 返回 None → 回傳 UNKNOWN
3. DA_IntentRAG 返回結果 → 直接透傳
4. UNKNOWN 結果包含 detect_query_complexity
5. get_cached_intent_matcher singleton
6. 各種 intent 類型正確透傳

所有 DA_IntentRAG 呼叫都透過 mock，無真實 Qdrant / Ollama 請求。
"""

from unittest.mock import AsyncMock, patch

import pytest

from data_agent.services.schema_driven_query.da_intent_rag import (
    DA_IntentRAG,
    IntentMatchResult,
    detect_query_complexity,
)
from data_agent.services.v5_intent_cache import (
    CachedIntentMatcher,
    get_cached_intent_matcher,
)


# ──────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singletons before and after each test."""
    DA_IntentRAG._instance = None
    import data_agent.services.v5_intent_cache as cache_mod

    cache_mod._singleton = None
    yield
    DA_IntentRAG._instance = None
    cache_mod._singleton = None


def _make_intent_result(
    intent: str = "QUERY_INVENTORY",
    confidence: float = 0.85,
    description: str = "在庫照会",
    input_filters: list | None = None,
    mart_table: str | None = "mart_inventory_wide",
    complexity: str = "simple",
) -> IntentMatchResult:
    """Helper: 建構 IntentMatchResult"""
    return IntentMatchResult(
        intent=intent,
        confidence=confidence,
        description=description,
        input_filters=input_filters or ["ITEM_NO"],
        mart_table=mart_table,
        complexity=complexity,
    )


# ──────────────────────────────────────────────────
# Tests: CachedIntentMatcher
# ──────────────────────────────────────────────────


class TestCachedIntentMatcher:
    """CachedIntentMatcher thin wrapper 測試"""

    @pytest.mark.asyncio
    async def test_match_intent_delegates_to_da_intent_rag(self):
        """match_intent 應委派給 DA_IntentRAG.get_instance().match_intent()"""
        mock_result = _make_intent_result()

        with patch.object(DA_IntentRAG, "get_instance", new_callable=AsyncMock) as mock_get:
            mock_rag = AsyncMock()
            mock_rag.match_intent = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_rag

            matcher = CachedIntentMatcher()
            result = await matcher.match_intent("查詢料號 NI001 的庫存")

        assert result.intent == "QUERY_INVENTORY"
        assert result.confidence == 0.85
        assert result.description == "在庫照会"
        assert result.complexity == "simple"
        mock_rag.match_intent.assert_awaited_once_with("查詢料號 NI001 的庫存")

    @pytest.mark.asyncio
    async def test_rag_returns_none_yields_unknown(self):
        """DA_IntentRAG 返回 None → CachedIntentMatcher 回傳 UNKNOWN"""
        with patch.object(DA_IntentRAG, "get_instance", new_callable=AsyncMock) as mock_get:
            mock_rag = AsyncMock()
            mock_rag.match_intent = AsyncMock(return_value=None)
            mock_get.return_value = mock_rag

            matcher = CachedIntentMatcher()
            result = await matcher.match_intent("完全不相關的內容")

        assert result.intent == "UNKNOWN"
        assert result.confidence == 0.0
        assert result.description == ""
        assert result.input_filters == []
        assert result.mart_table is None

    @pytest.mark.asyncio
    async def test_unknown_complexity_uses_detect_query_complexity(self):
        """UNKNOWN 結果的 complexity 由 detect_query_complexity 決定"""
        with patch.object(DA_IntentRAG, "get_instance", new_callable=AsyncMock) as mock_get:
            mock_rag = AsyncMock()
            mock_rag.match_intent = AsyncMock(return_value=None)
            mock_get.return_value = mock_rag

            matcher = CachedIntentMatcher()

            # Simple query
            result_simple = await matcher.match_intent("查詢料號的庫存")
            assert result_simple.intent == "UNKNOWN"
            assert result_simple.complexity == "simple"

            # Complex query (排序 keyword)
            result_complex = await matcher.match_intent("庫存排序統計")
            assert result_complex.intent == "UNKNOWN"
            assert result_complex.complexity == "complex"

    @pytest.mark.asyncio
    async def test_passthrough_all_intent_fields(self):
        """所有 IntentMatchResult 欄位都正確透傳"""
        mock_result = IntentMatchResult(
            intent="QUERY_SHIPPING",
            confidence=0.91,
            description="出荷通知照会",
            input_filters=["DOC_NO", "CUSTOMER_NO"],
            mart_table="mart_shipping_wide",
            complexity="complex",
        )

        with patch.object(DA_IntentRAG, "get_instance", new_callable=AsyncMock) as mock_get:
            mock_rag = AsyncMock()
            mock_rag.match_intent = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_rag

            matcher = CachedIntentMatcher()
            result = await matcher.match_intent("出貨查詢排序")

        assert result.intent == "QUERY_SHIPPING"
        assert result.confidence == 0.91
        assert result.description == "出荷通知照会"
        assert result.input_filters == ["DOC_NO", "CUSTOMER_NO"]
        assert result.mart_table == "mart_shipping_wide"
        assert result.complexity == "complex"

    @pytest.mark.asyncio
    async def test_work_order_intent_passthrough(self):
        """工單意圖正確透傳"""
        mock_result = _make_intent_result(
            intent="QUERY_WORK_ORDER",
            confidence=0.78,
            description="工單照会",
            input_filters=["MO_DOC_NO", "TIME_RANGE"],
            mart_table="mart_work_order_wide",
            complexity="simple",
        )

        with patch.object(DA_IntentRAG, "get_instance", new_callable=AsyncMock) as mock_get:
            mock_rag = AsyncMock()
            mock_rag.match_intent = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_rag

            matcher = CachedIntentMatcher()
            result = await matcher.match_intent("查詢工單 SF001 的狀態")

        assert result.intent == "QUERY_WORK_ORDER"
        assert result.mart_table == "mart_work_order_wide"

    @pytest.mark.asyncio
    async def test_match_intent_called_multiple_times(self):
        """多次呼叫 match_intent 每次都委派到 DA_IntentRAG"""
        results = [
            _make_intent_result(intent="QUERY_INVENTORY"),
            _make_intent_result(intent="QUERY_SHIPPING", description="出荷通知照会"),
        ]

        with patch.object(DA_IntentRAG, "get_instance", new_callable=AsyncMock) as mock_get:
            mock_rag = AsyncMock()
            mock_rag.match_intent = AsyncMock(side_effect=results)
            mock_get.return_value = mock_rag

            matcher = CachedIntentMatcher()
            r1 = await matcher.match_intent("庫存查詢")
            r2 = await matcher.match_intent("出貨查詢")

        assert r1.intent == "QUERY_INVENTORY"
        assert r2.intent == "QUERY_SHIPPING"
        assert mock_rag.match_intent.await_count == 2


class TestGetCachedIntentMatcher:
    """get_cached_intent_matcher factory 測試"""

    def test_returns_cached_intent_matcher(self):
        """get_cached_intent_matcher 返回 CachedIntentMatcher 實例"""
        matcher = get_cached_intent_matcher()
        assert isinstance(matcher, CachedIntentMatcher)

    def test_singleton_returns_same_instance(self):
        """get_cached_intent_matcher 返回同一個 singleton"""
        matcher1 = get_cached_intent_matcher()
        matcher2 = get_cached_intent_matcher()
        assert matcher1 is matcher2

    def test_new_instance_after_reset(self):
        """reset _singleton 後返回新實例"""
        import data_agent.services.v5_intent_cache as cache_mod

        matcher1 = get_cached_intent_matcher()
        cache_mod._singleton = None
        matcher2 = get_cached_intent_matcher()
        assert matcher1 is not matcher2
