# 代碼功能說明: V5 LLM SQL 生成服務 — 動態 schema + sqlglot 驗證 + 分層 fallback
# 創建日期: 2026-03-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx
import sqlglot
import structlog
from sqlglot.errors import ParseError

logger = structlog.get_logger(__name__)

DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_DEFAULT_MODEL", os.environ.get("MOE_CHAT_MODEL", "mistral-nemo:12b"))


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
        return f"""你是 DuckDB SQL 專家。根據用戶的自然語言查詢，生成可直接執行的 DuckDB SQL。

{schema_prompt}

## 重要規則：
1. **嚴禁跨表引用欄位**：每張表只能使用「可用表格」章節中列出的欄位。如果你需要的欄位不在該表中，不可以從其他表借用——請僅使用該表現有的欄位。
2. 只使用上述表格的實際欄位名稱（注意大小寫，例如 SFCBDOCNO 而非 sfcbdocno）
3. 只使用 SELECT 語句（只讀）
4. **嚴格限制輸出格式**：回覆中只能包含一條 SQL 語句，禁止輸出任何解釋、說明文字或 markdown 標記。不要寫「Here is」「以下是」等前綴。
5. 原始表格（非 mart_*）必須使用 read_parquet() 語法，例如: `SELECT col FROM read_parquet('s3://tiptop-raw/raw/v1/tiptop_jp/TABLE/year=*/month=*/data.parquet') WHERE ...`
6. Mart 表格（mart_*）直接使用表格名稱，例如: `SELECT col FROM mart_inventory_wide WHERE ...`

## SQL 品質規範（必須遵守）：
7. **禁止使用 SELECT ***：必須明確列出需要的欄位名稱。根據用戶查詢意圖選擇相關欄位。
8. **必須加 LIMIT**：
   - 明細查詢（用戶要求列表/明細/前N筆）：使用用戶指定的數量，若未指定預設 LIMIT 100
   - 聚合查詢（含 SUM/COUNT/AVG/GROUP BY）：預設 LIMIT 100
9. **METRIC 欄位聚合規則**：
   - 表格說明中標記為 `type=METRIC` 且帶有 `aggregation=SUM` 的欄位，在彙總統計時必須使用 SUM() 聚合
   - 標記為 `type=DIMENSION` 的欄位是分組維度，用於 GROUP BY
   - 當查詢需要「彙總」「統計」「合計」「各XX的」時，對 METRIC 欄位使用對應聚合函數
10. **GROUP BY 規則**：使用聚合函數時，SELECT 中所有非聚合欄位必須出現在 GROUP BY 中
11. **排序**：聚合查詢建議加 ORDER BY 讓結果更有意義（如 ORDER BY total DESC）
12. **欄位名稱必須完全匹配**：使用表格中列出的確切欄位名稱，不要自行拼接或猜測欄位名（例如不要把 SFCBDOCNO 寫成 sfcbadocno）

## 查詢類型判斷：
- 「列出/明細/前N筆/查詢XX的資料」→ 明細查詢：SELECT 具體欄位 + WHERE 條件 + LIMIT
- 「各XX統計/彙總/合計/有多少種」→ 聚合查詢：SELECT 維度 + SUM/COUNT(指標) + GROUP BY + ORDER BY + LIMIT
- 「大於/小於/超過」→ 篩選查詢：SELECT 具體欄位 + WHERE 條件 + LIMIT"""

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
        raw_text = result.get("response", "").strip()
        return self._extract_sql(raw_text)

    @staticmethod
    def _extract_sql(raw: str) -> str:
        """從 LLM 回應中提取純 SQL 語句。

        處理常見 LLM 輸出問題：
        - markdown 代碼塊 (```sql ... ```)
        - 前綴說明文字 ("Here is the query:")
        - 後綴解釋 ("This query returns ...")
        """
        if not raw:
            return ""

        # 1. 嘗試從 markdown 代碼塊中提取
        md_match = re.search(r"```(?:sql)?\s*\n?(.*?)\n?```", raw, re.DOTALL | re.IGNORECASE)
        if md_match:
            return md_match.group(1).strip()

        # 2. 嘗試用 SELECT 關鍵字定位 SQL 起始位置
        select_match = re.search(r"(SELECT\s.+)", raw, re.DOTALL | re.IGNORECASE)
        if select_match:
            sql_candidate = select_match.group(1).strip()
            # 移除 SQL 結尾後的自然語言解釋（以常見句首詞截斷）
            # 匹配：換行後跟英文/中文說明句
            tail_pattern = re.compile(
                r"\n\s*(?:"
                r"This |Here |The |Note[ :]|Explanation|It |I |--|//"
                r"|這|以上|此|說明|備註|注意|解釋"
                r").*",
                re.DOTALL | re.IGNORECASE,
            )
            sql_candidate = tail_pattern.split(sql_candidate, maxsplit=1)[0].strip()
            # 清除尾部分號後多餘文字
            semicolon_idx = sql_candidate.rfind(";")
            if semicolon_idx > 0:
                sql_candidate = sql_candidate[: semicolon_idx + 1]
            return sql_candidate

        # 3. Fallback: 原文清洗
        return raw.replace("```sql", "").replace("```", "").strip()

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
            # Attempt 1: first try with provided model
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
            except Exception as first_error:
                # If small model failed (timeout, connection error, etc.), escalate to big model
                if model != self.big_model:
                    logger.warning(
                        "small model failed, escalating to big model",
                        model=model,
                        error=str(first_error),
                    )
                    escalated = True
                    final_model = self.big_model
                    attempt_start = time.perf_counter()
                    final_sql = self._invoke_llm(
                        nlq=nlq,
                        schema_prompt=schema_prompt,
                        model=self.big_model,
                        timeout=self.big_model_timeout,
                    )
                    final_valid, parse_error = self._validate_sql(final_sql)
                    logger.info(
                        "LLM SQL generation attempt",
                        model=self.big_model,
                        attempt_number="1_escalated",
                        sqlglot_valid=final_valid,
                        latency_ms=(time.perf_counter() - attempt_start) * 1000,
                    )
                else:
                    # Big model already failed on first attempt
                    logger.error(
                        "big model LLM call failed on first attempt",
                        model=final_model,
                        error=str(first_error),
                        exc_info=True,
                    )
                    raise

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

            # If we escalated on first attempt, return error (don't retry with parse_error)
            if escalated:
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

            # Attempt 2: Retry with parse error hint (only if original model wasn't big model)
            if model != self.big_model:
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

                # Attempt 3: Escalate to big model
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
            else:
                # Big model on first attempt returned invalid SQL
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
