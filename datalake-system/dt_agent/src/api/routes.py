# 代碼功能說明: DT-Agent API 路由（從 data_agent v5_routes.py 移植）
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

import os
import time

import structlog
from fastapi import APIRouter

from dt_agent.src.api.models import V5ErrorDetails, V5ExecuteRequest, V5ExecuteResponse
from dt_agent.src.executor.duckdb_executor import get_simple_executor
from dt_agent.src.core.sql_generator import get_llm_sql_generator
from dt_agent.src.core.intent_resolver import get_cached_intent_matcher
from dt_agent.src.core.schema_builder import get_schema_builder
from dt_agent.src.core.sql_safety import validate_sql_safety
from dt_agent.src.core.query_guard import validate_query

logger = structlog.get_logger(__name__)

dt_router = APIRouter()
schema_builder = get_schema_builder()


@dt_router.get("/health")
async def health():
    return {"status": "healthy", "service": "dt-agent", "version": "1.0.0"}


@dt_router.post("/execute")
async def execute(request: V5ExecuteRequest):
    start = time.perf_counter()

    nlq = request.task_data.nlq
    return_mode = request.task_data.return_mode or "summary"

    logger.info("dt-agent received query", task_id=request.task_id, nlq=nlq)

    matcher = get_cached_intent_matcher()
    intent_result = await matcher.match_intent(nlq)

    # ── 前置驗證（Pre-validation Guardrail）──
    guard_result = validate_query(
        nlq=nlq,
        intent_name=intent_result.intent,
        mart_table=intent_result.mart_table,
    )
    if not guard_result.passed:
        logger.info(
            "QueryGuard 攔截查詢",
            nlq=nlq,
            intent=intent_result.intent,
            guard_type=guard_result.guard_type,
            reason=guard_result.reason,
        )
        return V5ExecuteResponse(
            success=False,
            error_type="pre_execution",
            error_code="QUERY_GUARD_REJECTED",
            message=guard_result.reason or "查詢前置驗證未通過",
            details=V5ErrorDetails(original_query=nlq),
            clarification_needed=guard_result.clarification_needed,
            suggestion=guard_result.suggestion,
            metadata={
                "matched_intent": intent_result.intent,
                "intent_confidence": intent_result.confidence,
                "complexity": intent_result.complexity,
                "model_used": None,
                "retries": 0,
                "escalated": False,
                "sqlglot_valid": False,
                "generation_time_ms": None,
                "guard_type": guard_result.guard_type,
                "total_time_ms": (time.perf_counter() - start) * 1000,
            },
        )

    small_model = os.environ.get("OLLAMA_DEFAULT_MODEL", "mistral-nemo:12b")
    big_model = os.environ.get("OLLAMA_BIG_MODEL", "gpt-oss:120b")
    small_timeout = 30.0
    big_timeout = 90.0
    confidence_threshold = 0.3

    try:
        if intent_result.confidence < confidence_threshold:
            model = big_model
            timeout = big_timeout
            schema_prompt = schema_builder.build_full_schema_prompt()
        elif intent_result.complexity == "complex":
            model = big_model
            timeout = big_timeout
            schema_prompt = schema_builder.build_schema_prompt(intent_result.intent, "complex")
        else:
            model = small_model
            timeout = small_timeout
            schema_prompt = schema_builder.build_schema_prompt(intent_result.intent, "simple")
    except Exception as error:
        logger.error("schema prompt build failed", error=str(error), exc_info=True)
        return V5ExecuteResponse(
            success=False,
            error_type="pre_execution",
            error_code="SCHEMA_PROMPT_BUILD_FAILED",
            message=f"Schema 構建失敗: {str(error)}",
            details=V5ErrorDetails(original_query=nlq),
            metadata={
                "matched_intent": intent_result.intent,
                "intent_confidence": intent_result.confidence,
                "complexity": intent_result.complexity,
                "model_used": None,
                "retries": 0,
                "escalated": False,
                "sqlglot_valid": False,
                "generation_time_ms": None,
                "total_time_ms": (time.perf_counter() - start) * 1000,
            },
        )

    generator = get_llm_sql_generator()
    sql_result = generator.generate_sql(
        nlq=nlq,
        schema_prompt=schema_prompt,
        model=model,
        timeout=timeout,
    )
    sql = sql_result.get("sql", "")

    if sql:
        safety = validate_sql_safety(sql)
        if not safety["safe"]:
            return V5ExecuteResponse(
                success=False,
                error_type="safety_violation",
                error_code="SQL_SAFETY_CHECK_FAILED",
                message=f"SQL 安全驗證失敗: {safety['reason']}",
                details=V5ErrorDetails(original_query=nlq, sql=sql),
                metadata={
                    "matched_intent": intent_result.intent,
                    "intent_confidence": intent_result.confidence,
                    "complexity": intent_result.complexity,
                    "model_used": sql_result.get("model_used"),
                    "retries": sql_result.get("retries", 0),
                    "escalated": sql_result.get("escalated", False),
                    "sqlglot_valid": False,
                    "generation_time_ms": sql_result.get("generation_time_ms"),
                    "total_time_ms": (time.perf_counter() - start) * 1000,
                },
            )

    if not sql or sql_result.get("status") == "error":
        return V5ExecuteResponse(
            success=False,
            error_type="pre_execution",
            error_code="SQL_GENERATION_FAILED",
            message="無法生成有效 SQL",
            details=V5ErrorDetails(original_query=nlq),
            metadata={
                "matched_intent": intent_result.intent,
                "intent_confidence": intent_result.confidence,
                "complexity": intent_result.complexity,
                "model_used": sql_result.get("model_used"),
                "retries": sql_result.get("retries", 0),
                "escalated": sql_result.get("escalated", False),
                "sqlglot_valid": False,
                "generation_time_ms": sql_result.get("generation_time_ms"),
                "total_time_ms": (time.perf_counter() - start) * 1000,
            },
        )

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
            metadata={
                "matched_intent": intent_result.intent,
                "intent_confidence": intent_result.confidence,
                "complexity": intent_result.complexity,
                "model_used": sql_result.get("model_used"),
                "retries": sql_result.get("retries", 0),
                "escalated": sql_result.get("escalated", False),
                "sqlglot_valid": sql_result.get("sqlglot_valid", False),
                "generation_time_ms": sql_result.get("generation_time_ms"),
                "total_time_ms": (time.perf_counter() - start) * 1000,
            },
        )
    except Exception as error:
        logger.error("SQL execution failed", error=str(error), exc_info=True)
        return V5ExecuteResponse(
            success=False,
            error_type="execution",
            error_code="SQL_EXECUTION_FAILED",
            message=f"SQL 執行失敗: {str(error)}",
            details=V5ErrorDetails(original_query=nlq, sql=sql),
            metadata={
                "matched_intent": intent_result.intent,
                "intent_confidence": intent_result.confidence,
                "complexity": intent_result.complexity,
                "model_used": sql_result.get("model_used"),
                "retries": sql_result.get("retries", 0),
                "escalated": sql_result.get("escalated", False),
                "sqlglot_valid": sql_result.get("sqlglot_valid", False),
                "generation_time_ms": sql_result.get("generation_time_ms"),
                "total_time_ms": (time.perf_counter() - start) * 1000,
            },
        )
