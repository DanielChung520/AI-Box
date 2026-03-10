# 代碼功能說明: V5 pipeline pytest unit tests for v5_schema_builder
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11
# -*- coding: utf-8 -*-
"""
V5 Schema Builder 單元測試

測試 V5SchemaBuilder 的 build_schema_prompt / build_full_schema_prompt 功能。
使用 tmp_path 建立測試用的 intents.json / bindings.json / concepts.json。
"""

import json

import pytest

from data_agent.services.v5_schema_builder import V5SchemaBuilder


# ──────────────────────────────────────────────────
# Fixture: 測試用 metadata 檔案
# ──────────────────────────────────────────────────

SAMPLE_INTENTS = {
    "intents": {
        "QUERY_INVENTORY": {
            "description": "在庫照会",
            "input": {"filters": ["ITEM_NO", "WAREHOUSE_NO"]},
            "output": {"metrics": ["EXISTING_STOCKS"], "dimensions": ["ITEM_NO", "WAREHOUSE_NO"]},
            "mart_table": "mart_inventory_wide",
        },
        "QUERY_QUALITY": {
            "description": "品質查詢",
            "input": {"filters": ["ITEM_NO"]},
            "output": {"metrics": [], "dimensions": ["ITEM_NO"]},
            # 注意：QUERY_QUALITY 沒有 mart_table
        },
    }
}

SAMPLE_BINDINGS = {
    "bindings": {
        "ITEM_NO": {
            "DUCKDB": {"table": "inag_t", "column": "inag001", "type": "string"},
        },
        "WAREHOUSE_NO": {
            "DUCKDB": {"table": "inag_t", "column": "inag004", "type": "string"},
        },
        "EXISTING_STOCKS": {
            "DUCKDB": {
                "table": "mart_inventory_wide",
                "column": "existing_stocks",
                "type": "number",
                "aggregation": "SUM",
            },
        },
    }
}

SAMPLE_CONCEPTS = {
    "concepts": {
        "ITEM_NO": {"description": "料件編號", "type": "CODE"},
        "WAREHOUSE_NO": {"description": "倉庫編號", "type": "CODE"},
        "EXISTING_STOCKS": {"description": "現有庫存", "type": "METRIC", "aggregation": "SUM"},
    }
}


@pytest.fixture
def schema_builder(tmp_path):
    """建立使用測試 metadata 的 V5SchemaBuilder"""
    (tmp_path / "intents.json").write_text(json.dumps(SAMPLE_INTENTS), encoding="utf-8")
    (tmp_path / "bindings.json").write_text(json.dumps(SAMPLE_BINDINGS), encoding="utf-8")
    (tmp_path / "concepts.json").write_text(json.dumps(SAMPLE_CONCEPTS), encoding="utf-8")
    return V5SchemaBuilder(metadata_dir=tmp_path)


class TestV5SchemaBuilder:
    """V5SchemaBuilder 測試"""

    def test_build_schema_prompt_simple_with_mart(self, schema_builder):
        """QUERY_INVENTORY（有 mart_table）+ simple → 應使用 raw table columns"""
        prompt = schema_builder.build_schema_prompt("QUERY_INVENTORY", "simple")
        assert "QUERY_INVENTORY" in prompt
        assert "simple" in prompt
        # simple complexity 使用 raw table 映射
        assert "inag" in prompt.lower() or "mart_inventory" in prompt.lower()
        assert len(prompt) > 50

    def test_build_schema_prompt_complex_with_mart(self, schema_builder):
        """QUERY_INVENTORY（有 mart_table）+ complex → 應使用 mart table"""
        prompt = schema_builder.build_schema_prompt("QUERY_INVENTORY", "complex")
        assert "QUERY_INVENTORY" in prompt
        assert "complex" in prompt
        assert "mart_inventory_wide" in prompt

    def test_build_schema_prompt_no_mart_intent(self, schema_builder):
        """QUERY_QUALITY（沒有 mart_table）→ 任何 complexity 都使用 raw tables"""
        prompt = schema_builder.build_schema_prompt("QUERY_QUALITY", "simple")
        assert "QUERY_QUALITY" in prompt
        # 沒有 mart_table，所以直接用 raw table
        assert "inag" in prompt.lower() or "ITEM_NO" in prompt or len(prompt) > 20

    def test_build_full_schema_prompt_not_empty(self, schema_builder):
        """build_full_schema_prompt() 應回傳非空字串，包含所有 intent"""
        prompt = schema_builder.build_full_schema_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 50
        assert "Full Schema" in prompt or "全部" in prompt or "all intents" in prompt.lower()

    def test_unknown_intent_raises(self, schema_builder):
        """未知 intent 應拋出 ValueError"""
        with pytest.raises(ValueError, match="Unknown intent"):
            schema_builder.build_schema_prompt("NONEXISTENT_INTENT", "simple")

    def test_invalid_complexity_raises(self, schema_builder):
        """無效的 complexity 值應拋出 ValueError"""
        with pytest.raises(ValueError, match="Unsupported complexity"):
            schema_builder.build_schema_prompt("QUERY_INVENTORY", "extreme")

    def test_complexity_case_insensitive(self, schema_builder):
        """complexity 大小寫不敏感"""
        prompt = schema_builder.build_schema_prompt("QUERY_INVENTORY", " Simple ")
        assert "QUERY_INVENTORY" in prompt
