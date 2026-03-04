# 代碼功能說明: v5 API 路由
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

import logging
from fastapi import APIRouter

from data_agent.models import V5ExecuteRequest, V5ExecuteResponse, V5ErrorDetails

logger = logging.getLogger(__name__)

V5_router = APIRouter()

# 複雜查詢關鍵詞
COMPLEX_QUERY_KEYWORDS = [
    "最大",
    "最多",
    "最少",
    "最低",
    "最高",
    "排序",
    "前",
    "名",
    "佔比",
    "比例",
    "百分比",
    "比較",
    "對比",
    "總計",
    "合計",
    "小計",
]


def detect_query_complexity(query: str) -> str:
    """根據查詢內容判斷複雜度"""
    for keyword in COMPLEX_QUERY_KEYWORDS:
        if keyword in query:
            return "complex"
    return "simple"


@V5_router.get("/v5/health")
async def v5_health():
    return {"status": "healthy", "service": "data-agent-v5", "version": "1.0.0"}


def _generate_fallback_sql(nlq: str) -> str:
    import re

    item_match = re.search(r"料號[：:]?\s*([A-Za-z0-9]+)", nlq)
    if item_match:
        item_no = item_match.group(1)
        return f"SELECT * FROM mart_inventory_wide WHERE item_no = '{item_no}' LIMIT 1000"
    return "SELECT * FROM mart_inventory_wide LIMIT 10"


@V5_router.post("/v5/execute")
async def v5_execute(request: V5ExecuteRequest):
    from data_agent.services.simple_llm_sql import get_llm_sql_generator

    logger.info(f"v5 received query: task_id={request.task_id}, nlq={request.task_data.nlq}")

    nlq = request.task_data.nlq
    return_mode = request.task_data.return_mode or "summary"

    # 1. 意圖識別 + 複雜度判斷
    complexity = detect_query_complexity(nlq)
    if complexity == "complex":
        selected_model = "gpt-oss:120b"
    else:
        selected_model = "llama3:8b"

    logger.info(f"[ModelRouter] complexity={complexity}, model={selected_model}")

    # 2. LLM 生成 SQL
    generator = get_llm_sql_generator()
    sql_result = generator.generate_sql(nlq, return_mode, model=selected_model)

    # 前置異常處理
    if sql_result.get("status") == "pre_error":
        error = sql_result["error"]
        return V5ExecuteResponse(
            success=False,
            error_type=error.get("error_type"),
            error_code=error.get("error_code"),
            message=error.get("message"),
            details=V5ErrorDetails(
                original_query=nlq,
                ambiguity=error.get("details", {}).get("ambiguity"),
            )
            if error.get("details")
            else None,
            clarification_needed=error.get("clarification_needed"),
            suggestion=error.get("suggestion"),
        )

    sql = sql_result.get("sql", "")
    if not sql:
        return V5ExecuteResponse(
            success=False,
            error_type="pre_execution",
            error_code="SQL_GENERATION_FAILED",
            message="無法生成 SQL",
            details=V5ErrorDetails(original_query=nlq),
        )

    # 3. 執行 SQL
    from data_agent.services.simple_executor import get_simple_executor

    executor = get_simple_executor()

    try:
        exec_result = executor.execute(sql, return_mode=return_mode)
        return V5ExecuteResponse(
            success=True,
            sql=sql,
            data=exec_result.get("data"),
            row_count=exec_result.get("row_count"),
            columns=exec_result.get("columns"),
            pagination=exec_result.get("pagination"),
            execution_time_ms=exec_result.get("execution_time_ms"),
        )
    except Exception as e:
        logger.error(f"SQL execution failed: {e}")
        # 使用備用 SQL 重試
        fallback_sql = _generate_fallback_sql(nlq)
        logger.info(f"Retrying with fallback SQL: {fallback_sql}")
        try:
            exec_result = executor.execute(fallback_sql, return_mode=return_mode)
            return V5ExecuteResponse(
                success=True,
                sql=fallback_sql,
                data=exec_result.get("data"),
                row_count=exec_result.get("row_count"),
                columns=exec_result.get("columns"),
                pagination=exec_result.get("pagination"),
                execution_time_ms=exec_result.get("execution_time_ms"),
                warning="Used fallback SQL due to execution error",
            )
        except Exception as e2:
            return V5ExecuteResponse(
                success=False,
                error_type="execution",
                error_code="SQL_EXECUTION_FAILED",
                message=f"SQL 執行失敗: {str(e2)}",
                details=V5ErrorDetails(original_query=nlq, sql_generated=sql),
            )
