# 代碼功能說明: V5 pipeline pytest unit tests for v5_intent_cache
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11
# -*- coding: utf-8 -*-
"""
V5 Intent Cache 單元測試

測試 CachedIntentMatcher 的語意匹配功能。
所有 embedding 呼叫都透過 mock 避免真實 Ollama API 呼叫。
"""

import json

import numpy as np
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from data_agent.services.v5_intent_cache import CachedIntentMatcher


# ──────────────────────────────────────────────────
# Test data
# ──────────────────────────────────────────────────

SAMPLE_INTENTS = {
    "intents": {
        "QUERY_INVENTORY": {
            "description": "在庫照会",
            "input": {"filters": ["ITEM_NO", "WAREHOUSE_NO"]},
            "output": {"metrics": ["EXISTING_STOCKS"], "dimensions": ["ITEM_NO"]},
            "mart_table": "mart_inventory_wide",
        },
        "QUERY_WORK_ORDER": {
            "description": "工單查詢",
            "input": {"filters": ["TIME_RANGE"]},
            "output": {"metrics": ["WORK_ORDER_COUNT"], "dimensions": []},
            "mart_table": "mart_work_order_wide",
        },
    }
}


def _make_embedding(seed: int, dim: int = 384) -> list:
    """產生可重現的假 embedding 向量"""
    rng = np.random.RandomState(seed)
    vec = rng.randn(dim).astype(np.float32)
    return (vec / np.linalg.norm(vec)).tolist()


# inventory 和 work_order 的 embedding 應有所不同
INVENTORY_VEC = _make_embedding(42)
WORK_ORDER_VEC = _make_embedding(99)


@pytest.fixture
def intents_file(tmp_path):
    """建立測試用 intents.json"""
    path = tmp_path / "intents.json"
    path.write_text(json.dumps(SAMPLE_INTENTS), encoding="utf-8")
    return str(path)


def _build_mock_embed_manager(query_vec: list):
    """建構 mock EmbeddingManager，可自定義 query embedding 回傳值"""
    mock_manager = AsyncMock()
    # 每次 embed() 呼叫：前兩次回傳 intent embedding，後續回傳 query embedding
    call_count = 0

    async def embed_side_effect(text: str):
        nonlocal call_count
        call_count += 1
        # 前面的呼叫是 _ensure_cache（intent embedding）
        if call_count == 1:
            return INVENTORY_VEC
        elif call_count == 2:
            return WORK_ORDER_VEC
        else:
            # query embedding
            return query_vec

    mock_manager.embed = AsyncMock(side_effect=embed_side_effect)
    return mock_manager


class TestCachedIntentMatcher:
    """CachedIntentMatcher 測試"""

    @pytest.mark.asyncio
    async def test_match_intent_returns_result_with_fields(self, intents_file):
        """match_intent 應回傳含 intent、confidence、description 等欄位的結果"""
        # query embedding 與 INVENTORY_VEC 相同 → 應匹配 QUERY_INVENTORY
        mock_manager = _build_mock_embed_manager(INVENTORY_VEC)

        matcher = CachedIntentMatcher(intents_file=intents_file, confidence_threshold=0.3)

        with patch.object(matcher, "_get_embedding_manager", return_value=mock_manager):
            result = await matcher.match_intent("查詢料號 NI001 的庫存")

        assert result.intent == "QUERY_INVENTORY"
        assert result.confidence > 0.3
        assert hasattr(result, "description")
        assert hasattr(result, "input_filters")
        assert hasattr(result, "mart_table")
        assert hasattr(result, "complexity")

    @pytest.mark.asyncio
    async def test_cache_hit_on_second_call(self, intents_file):
        """第二次呼叫應使用快取，不再重新計算 intent embeddings"""
        mock_manager = AsyncMock()
        # 所有 embed 呼叫回傳相同向量
        mock_manager.embed = AsyncMock(return_value=INVENTORY_VEC)

        matcher = CachedIntentMatcher(intents_file=intents_file, confidence_threshold=0.3)

        with patch.object(matcher, "_get_embedding_manager", return_value=mock_manager):
            # 第一次呼叫：載入 intents + 計算 intent embeddings + query embedding
            result1 = await matcher.match_intent("庫存查詢")
            embed_calls_after_first = mock_manager.embed.call_count

            # 第二次呼叫：只需 query embedding（快取已建立）
            result2 = await matcher.match_intent("在庫查詢")
            embed_calls_after_second = mock_manager.embed.call_count

        # 第一次：2 intent embed + 1 query = 3 次
        assert embed_calls_after_first == 3
        # 第二次：只有 1 次 query embed（快取命中）
        assert embed_calls_after_second == 4  # 3 + 1

    @pytest.mark.asyncio
    async def test_low_confidence_returns_unknown(self, intents_file):
        """當所有 intent 的 cosine similarity 都低於閾值時，應回傳 UNKNOWN"""
        # 使用一個與任何 intent 都不相似的向量
        orthogonal_vec = [0.0] * 384
        orthogonal_vec[0] = 1.0  # 一個極端方向的向量

        mock_manager = AsyncMock()
        call_count = 0

        async def embed_side_effect(text: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return INVENTORY_VEC
            elif call_count == 2:
                return WORK_ORDER_VEC
            else:
                return orthogonal_vec

        mock_manager.embed = AsyncMock(side_effect=embed_side_effect)

        # 設定很高的閾值，確保匹配失敗
        matcher = CachedIntentMatcher(intents_file=intents_file, confidence_threshold=0.99)

        with patch.object(matcher, "_get_embedding_manager", return_value=mock_manager):
            result = await matcher.match_intent("一些完全不相關的內容")

        assert result.intent == "UNKNOWN"
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_missing_intents_file_returns_unknown(self, tmp_path):
        """當 intents.json 不存在時，應 graceful 回傳 UNKNOWN"""
        missing_file = str(tmp_path / "nonexistent_intents.json")
        matcher = CachedIntentMatcher(intents_file=missing_file, confidence_threshold=0.3)

        mock_manager = AsyncMock()
        mock_manager.embed = AsyncMock(return_value=INVENTORY_VEC)

        with patch.object(matcher, "_get_embedding_manager", return_value=mock_manager):
            result = await matcher.match_intent("查詢庫存")

        assert result.intent == "UNKNOWN"
        assert result.confidence == 0.0
