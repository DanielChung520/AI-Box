# 代碼功能說明: V5 pipeline pytest unit tests for simple_llm_sql
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11
# -*- coding: utf-8 -*-
"""
SimpleLLMSQLGenerator 單元測試

測試 generate_sql() 的 happy path、retry、escalation 和回傳結構。
所有 Ollama /api/generate 呼叫都透過 mock 避免真實 API 呼叫。
"""

import pytest
from unittest.mock import patch, MagicMock

from data_agent.services.simple_llm_sql import SimpleLLMSQLGenerator


def _mock_ollama_response(sql_text: str) -> MagicMock:
    """建構 mock httpx Response，回傳指定的 SQL"""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": sql_text}
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


class TestSimpleLLMSQLGenerator:
    """SimpleLLMSQLGenerator 測試"""

    @pytest.fixture
    def generator(self):
        """建立測試用的 generator（不會真正連接 Ollama）"""
        gen = SimpleLLMSQLGenerator(
            ollama_host="http://localhost:11434",
            model="llama3:8b",
        )
        return gen

    def test_happy_path_returns_sql(self, generator):
        """第一次呼叫就回傳有效 SELECT → status=success"""
        valid_sql = (
            "SELECT item_no, existing_stocks FROM mart_inventory_wide WHERE item_no = 'NI001'"
        )

        with patch.object(generator.client, "post", return_value=_mock_ollama_response(valid_sql)):
            result = generator.generate_sql(
                nlq="查詢 NI001 的庫存",
                schema_prompt="## mart_inventory_wide\n| item_no | existing_stocks |",
                model="llama3:8b",
                timeout=30.0,
            )

        assert result["status"] == "success"
        assert result["sql"] == valid_sql
        assert result["sqlglot_valid"] is True  # sqlglot_validated 對應 sqlglot_valid
        assert result["model_used"] == "llama3:8b"
        assert result["retries"] == 0
        assert result["escalated"] is False
        assert result["error"] is None

    def test_retry_on_invalid_sql(self, generator):
        """第一次回傳 garbage → retry → 第二次回傳有效 SQL"""
        garbage_sql = "THIS IS NOT SQL AT ALL !!!"
        valid_sql = "SELECT item_no FROM mart_inventory_wide"

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _mock_ollama_response(garbage_sql)
            else:
                return _mock_ollama_response(valid_sql)

        with patch.object(generator.client, "post", side_effect=side_effect):
            result = generator.generate_sql(
                nlq="查詢庫存",
                schema_prompt="## schema",
                model="llama3:8b",
                timeout=30.0,
            )

        assert result["status"] == "success"
        assert result["sql"] == valid_sql
        assert result["sqlglot_valid"] is True
        assert result["retries"] == 1

    def test_escalation_on_persistent_failure(self, generator):
        """兩次 retry 都失敗 → escalate to big model → 仍失敗 → status=error"""
        garbage = "DEFINITELY_NOT_VALID_SQL @@@"

        with patch.object(generator.client, "post", return_value=_mock_ollama_response(garbage)):
            result = generator.generate_sql(
                nlq="查詢庫存",
                schema_prompt="## schema",
                model="llama3:8b",
                timeout=30.0,
            )

        assert result["status"] == "error"
        assert result["escalated"] is True
        assert result["sqlglot_valid"] is False
        assert result["model_used"] == "gpt-oss:120b"
        assert result["error"] is not None

    def test_return_structure(self, generator):
        """驗證回傳字典包含所有必要 key"""
        valid_sql = "SELECT 1"

        with patch.object(generator.client, "post", return_value=_mock_ollama_response(valid_sql)):
            result = generator.generate_sql(
                nlq="test",
                schema_prompt="## test",
                model="llama3:8b",
                timeout=30.0,
            )

        required_keys = {"sql", "model_used", "retries", "sqlglot_valid"}
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - result.keys()}"
        )
        # 額外驗證完整 key set
        expected_keys = {
            "sql",
            "status",
            "model_used",
            "retries",
            "escalated",
            "sqlglot_valid",
            "generation_time_ms",
            "error",
        }
        assert expected_keys == set(result.keys()), (
            f"Unexpected keys: {set(result.keys()) - expected_keys}"
        )

    def test_escalation_skipped_when_already_big_model(self, generator):
        """當初始 model 就是 big_model 且第一次失敗 → 不做 retry/escalation"""
        garbage = "DEFINITELY_NOT_VALID_SQL @@@"

        with patch.object(generator.client, "post", return_value=_mock_ollama_response(garbage)):
            result = generator.generate_sql(
                nlq="test",
                schema_prompt="## test",
                model="gpt-oss:120b",  # 已經是 big model
                timeout=30.0,
            )

        assert result["status"] == "error"
        assert result["escalated"] is False
        assert result["retries"] == 0

    def test_exception_during_llm_call(self, generator):
        """LLM 呼叫拋出異常 → 應回傳 error 狀態而非 crash"""
        with patch.object(generator.client, "post", side_effect=Exception("Connection refused")):
            result = generator.generate_sql(
                nlq="test",
                schema_prompt="## test",
                model="llama3:8b",
                timeout=30.0,
            )

        assert result["status"] == "error"
        assert "Connection refused" in result["error"]
        assert isinstance(result["generation_time_ms"], float)
