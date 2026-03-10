# 代碼功能說明: V5 LLM SQL 生成服務 — 動態 schema + sqlglot 驗證 + 分層 fallback
# 創建日期: 2026-03-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import sqlglot
import structlog
from sqlglot.errors import ParseError

logger = structlog.get_logger(__name__)

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("MOE_CHAT_MODEL", "llama3.2:3b-instruct-q4_0")


class SimpleLLMSQLGenerator:
    def __init__(
        self,
        ollama_host: str = DEFAULT_OLLAMA_HOST,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self.ollama_host = ollama_host
        self.model = model
        self.big_model = "gpt-oss:120b"
        self.big_model_timeout = 90.0
        self.client = httpx.Client(timeout=60.0)

    def _build_system_prompt(self, schema_prompt: str) -> str:
        return f"""你是 SQL 專家。根據用戶的自然語言查詢，生成 DuckDB SQL。

{schema_prompt}

## 重要規則：
1. 只使用上述表格的實際欄位名稱
2. 只使用 SELECT 語句（只讀）
3. 直接輸出 SQL，不要包含任何解釋或 markdown 標記
"""

    def _invoke_llm(
        self,
        *,
        nlq: str,
        schema_prompt: str,
        model: str,
        timeout: float,
        correction_hint: str | None = None,
    ) -> str:
        user_prompt = f"用戶查詢：{nlq}"
        if correction_hint:
            user_prompt = (
                f"{user_prompt}\n\n"
                "上一次 SQL 無法通過 sqlglot(DuckDB) 解析。"
                f"\n解析錯誤：{correction_hint}"
                "\n請修正 SQL 並僅輸出可執行 DuckDB SELECT 語句。"
            )

        response = self.client.post(
            f"{self.ollama_host}/api/generate",
            json={
                "model": model,
                "prompt": user_prompt,
                "system": self._build_system_prompt(schema_prompt),
                "stream": False,
            },
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        sql = result.get("response", "").strip()
        return sql.replace("```sql", "").replace("```", "").strip()

    def _validate_sql(self, sql: str) -> tuple[bool, str | None]:
        try:
            sqlglot.parse(sql, dialect="duckdb")
            normalized_sql = sql.strip().upper()
            if not normalized_sql.startswith("SELECT"):
                return False, "sqlglot parse succeeded but SQL is not a SELECT statement"
            return True, None
        except ParseError as error:
            return False, str(error)

    def generate_sql(
        self,
        nlq: str,
        schema_prompt: str,
        model: str,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        start = time.perf_counter()
        retries = 0
        escalated = False
        final_sql = ""
        final_model = model
        final_valid = False

        def elapsed_ms() -> float:
            return (time.perf_counter() - start) * 1000

        try:
            attempt_start = time.perf_counter()
            final_sql = self._invoke_llm(
                nlq=nlq,
                schema_prompt=schema_prompt,
                model=model,
                timeout=timeout,
            )
            final_valid, parse_error = self._validate_sql(final_sql)
            logger.info(
                "LLM SQL generation attempt",
                model=model,
                attempt_number=1,
                sqlglot_valid=final_valid,
                latency_ms=(time.perf_counter() - attempt_start) * 1000,
            )

            if final_valid:
                return {
                    "sql": final_sql,
                    "status": "success",
                    "model_used": final_model,
                    "retries": retries,
                    "escalated": escalated,
                    "sqlglot_valid": True,
                    "generation_time_ms": elapsed_ms(),
                    "error": None,
                }

            if model == self.big_model:
                return {
                    "sql": final_sql,
                    "status": "error",
                    "model_used": final_model,
                    "retries": retries,
                    "escalated": escalated,
                    "sqlglot_valid": False,
                    "generation_time_ms": elapsed_ms(),
                    "error": f"sqlglot parse failed: {parse_error}",
                }

            retries = 1
            attempt_start = time.perf_counter()
            final_sql = self._invoke_llm(
                nlq=nlq,
                schema_prompt=schema_prompt,
                model=model,
                timeout=30.0,
                correction_hint=parse_error,
            )
            final_valid, retry_error = self._validate_sql(final_sql)
            logger.info(
                "LLM SQL generation attempt",
                model=model,
                attempt_number=2,
                sqlglot_valid=final_valid,
                latency_ms=(time.perf_counter() - attempt_start) * 1000,
            )

            if final_valid:
                return {
                    "sql": final_sql,
                    "status": "success",
                    "model_used": final_model,
                    "retries": retries,
                    "escalated": escalated,
                    "sqlglot_valid": True,
                    "generation_time_ms": elapsed_ms(),
                    "error": None,
                }

            escalated = True
            final_model = self.big_model
            attempt_start = time.perf_counter()
            final_sql = self._invoke_llm(
                nlq=nlq,
                schema_prompt=schema_prompt,
                model=self.big_model,
                timeout=self.big_model_timeout,
                correction_hint=retry_error,
            )
            final_valid, escalation_error = self._validate_sql(final_sql)
            logger.info(
                "LLM SQL generation attempt",
                model=self.big_model,
                attempt_number=3,
                sqlglot_valid=final_valid,
                latency_ms=(time.perf_counter() - attempt_start) * 1000,
            )

            if final_valid:
                return {
                    "sql": final_sql,
                    "status": "success",
                    "model_used": final_model,
                    "retries": retries,
                    "escalated": escalated,
                    "sqlglot_valid": True,
                    "generation_time_ms": elapsed_ms(),
                    "error": None,
                }

            return {
                "sql": final_sql,
                "status": "error",
                "model_used": final_model,
                "retries": retries,
                "escalated": escalated,
                "sqlglot_valid": False,
                "generation_time_ms": elapsed_ms(),
                "error": f"sqlglot parse failed: {escalation_error}",
            }
        except Exception as error:
            logger.error(
                "LLM SQL generation failed",
                model=final_model,
                retries=retries,
                escalated=escalated,
                error=str(error),
                exc_info=True,
            )
            return {
                "sql": final_sql,
                "status": "error",
                "model_used": final_model,
                "retries": retries,
                "escalated": escalated,
                "sqlglot_valid": final_valid,
                "generation_time_ms": elapsed_ms(),
                "error": str(error),
            }


_generator: SimpleLLMSQLGenerator | None = None


def get_llm_sql_generator() -> SimpleLLMSQLGenerator:
    global _generator
    if _generator is None:
        _generator = SimpleLLMSQLGenerator()
    return _generator
