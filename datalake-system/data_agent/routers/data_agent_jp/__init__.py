# 代碼功能說明: Data-Agent-JP API 路由
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Data-Agent-JP API 路由

端點：
- POST /api/v1/data-agent/jp/execute - 執行查詢（SSE 階段回報）
- GET /api/v1/data-agent/jp/health - 健康檢查
"""

import logging
import asyncio
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from data_agent.services.i18n import t, get_locale
from data_agent.services.schema_driven_query.models import (
    ExecuteRequest,
    HealthResponse,
    QueryResult,
)
from data_agent.services.schema_driven_query.pre_validator import PreValidator
from data_agent.services.schema_driven_query.response_builder import (
    ResponseBuilder,
    StructuredResponse,
    ErrorCode,
)
from data_agent.services.schema_driven_query.resolver import Resolver, ResolverError
from data_agent.services.schema_driven_query.executor import (
    SQLExecutor,
    SQLExecutionError,
    ExecutorFactory,
    get_executor,
)
from data_agent.services.schema_driven_query.config import get_config
from data_agent.services.schema_driven_query.sse_emitter import get_event_emitter, SSEEventEmitter

logger = logging.getLogger(__name__)

router = APIRouter()


def get_resolver() -> Resolver:
    """獲取 Resolver 實例"""
    resolver = Resolver()
    resolver.load_schemas()
    return resolver


def get_config():
    """獲取配置"""
    from data_agent.services.schema_driven_query.config import get_config as _get_config

    return _get_config()


def get_executor():
    """獲取 SQL Executor 實例（使用 ExecutorFactory）"""
    from data_agent.services.schema_driven_query.executor import ExecutorFactory

    config = get_config()
    logger.info(f"Executor config datasource: {config.datasource}")
    factory = ExecutorFactory(config=config)
    executor = factory.get_executor()
    logger.info(f"Executor type: {type(executor).__name__}")
    return executor


@router.get("/v4/health", response_model=HealthResponse)
async def health():
    """
    健康檢查

    Returns:
        HealthResponse: 健康狀態
    """
    return HealthResponse(status="healthy", service="data-agent-v4", version="1.0.0")


@router.post("/v4/execute", response_model=StructuredResponse)
async def execute_query(
    request: ExecuteRequest,
    resolver: Resolver = Depends(get_resolver),
    executor: SQLExecutor = Depends(get_executor),
) -> StructuredResponse:
    """
    執行 Schema Driven Query

    使用 ResponseBuilder 產生結構化回應

    Args:
        request: 執行請求

    Returns:
        StructuredResponse: 結構化執行結果
    """
    logger.info(f"Received query request: task_id={request.task_id}")

    # 使用 ResponseBuilder
    builder = ResponseBuilder(task_id=request.task_id)
    builder.start_timing()

    # SSE 事件發射器
    emitter = get_event_emitter()

    try:
        # 階段 1: 接收到請求
        await emitter.request_received(request.task_id, request.task_data.nlq)

        # 1. 解析 NLQ
        resolve_result = resolver.resolve(request.task_data.nlq)

        if resolve_result["status"] == "error":
            error_code = resolve_result.get("error_code", "INTERNAL_ERROR")
            message = resolve_result.get("message", "Unknown error")

            # 映射錯誤碼
            mapped_code = ErrorCode.INTERNAL_ERROR.value
            if error_code == "SCHEMA_NOT_FOUND":
                mapped_code = ErrorCode.SCHEMA_NOT_FOUND.value
            elif error_code == "INTENT_UNCLEAR":
                mapped_code = ErrorCode.INTENT_UNCLEAR.value

            # 錯誤事件
            await emitter.error(request.task_id, mapped_code, message)

            return builder.build_error(
                error_code=mapped_code,
                message=message,
                suggestions=resolve_result.get("suggestions", []),
            )

        # 階段 2: 確認 Schema
        schema_used = resolve_result.get("schema_used", "unknown")
        tables = resolve_result.get("tables_used", [])
        columns = resolve_result.get("columns_used", [])
        await emitter.schema_confirmed(request.task_id, schema_used, tables, columns)

        # 階段 3: SQL 已產生
        sql = resolve_result["sql"]
        intent = resolve_result.get("intent", "UNKNOWN")
        await emitter.sql_generated(request.task_id, sql, intent)

        # 執行前置驗證
        validator = PreValidator()
        entities = resolve_result.get("params", {})
        validation_result = await validator.validate(
            request.task_data.nlq,
            intent,
            entities,
            intent_confidence=resolve_result.get("confidence", 1.0),
        )

        if not validation_result.valid:
            errors = validation_result.errors
            first_error = errors[0] if errors else None
            if first_error:
                error_code = first_error.code
                user_message = first_error.message
                suggestions = first_error.suggestions or []
                await emitter.error(request.task_id, error_code, user_message)
                return builder.build_error(
                    error_code=error_code,
                    message=user_message,
                    suggestions=suggestions,
                )

        # 階段 4: 執行查詢
        timeout = request.task_data.options.timeout
        await emitter.query_executing(request.task_id, timeout)

        # 2. 執行 SQL
        exec_result = executor.execute(sql, timeout)

        # 階段 5: 查詢完成
        row_count = len(exec_result.get("data", []))
        execution_time_ms = exec_result.get("execution_time_ms", 0)
        await emitter.query_completed(request.task_id, row_count, execution_time_ms)

        # 階段 5.5: 驗證結果
        await emitter.result_validating(request.task_id)

        # 建立分頁資訊
        page_size = (
            request.task_data.options.limit
            if request.task_data.options and request.task_data.options.limit
            else 100
        )
        pagination = {
            "page": 1,
            "page_size": page_size,
            "total_rows": row_count,
            "total_pages": (row_count + page_size - 1) // page_size if page_size > 0 else 1,
        }

        # Token 使用量（預設 - 實際應從 LLM 獲取）
        token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # 3. 返回成功回應
        response = builder.build_success(
            sql=sql,
            data=exec_result["data"],
            schema_used=schema_used,
            pagination=pagination,
            token_usage=token_usage,
        )

        # 階段 6: 返回結果
        await emitter.result_ready(request.task_id, "success", row_count)

        return response

    except ResolverError as e:
        logger.error(f"Resolver error: {e}")
        error_code = e.state.value if hasattr(e.state, "value") else "INTERNAL_ERROR"
        await emitter.error(request.task_id, error_code, e.message)
        return builder.build_error(
            error_code=error_code,
            message=e.message,
            suggestions=getattr(e, "suggestions", []),
        )

    except SQLExecutionError as e:
        logger.error(f"SQL execution error: {e}")
        error_code = ErrorCode.CONNECTION_TIMEOUT.value
        await emitter.error(request.task_id, error_code, str(e))
        return builder.build_error(
            error_code=error_code,
            message=str(e),
            exception=str(e),
        )

    except Exception as e:
        error_msg = str(e)
        error_code = "INTERNAL_ERROR"
        user_message = error_msg

        if "DuckDB Execution Error" in error_msg:
            if "table with name" in error_msg.lower() and "does not exist" in error_msg.lower():
                error_code = "SCHEMA_NOT_FOUND"
                user_message = "數據來源不足：表格不存在或尚未載入"
            elif "ambiguous reference" in error_msg.lower():
                error_code = "AMBIGUOUS_REFERENCE"
                user_message = "維度模糊：請更具體指定查詢維度"
            elif "referenced column" in error_msg.lower():
                error_code = "COLUMN_NOT_FOUND"
                user_message = "缺乏關鍵欄位：請確認查詢維度是否正確"
            elif "binder error" in error_msg.lower():
                error_code = "BINDER_ERROR"
                user_message = "缺乏關鍵欄位：請確認查詢維度是否正確"
            elif "out of memory" in error_msg.lower():
                error_code = "OUT_OF_MEMORY"
                user_message = "查詢記憶體不足：請減少查詢範圍"
            elif "null" in error_msg.lower() and "column" in error_msg.lower():
                error_code = "NULL_VALUE"
                user_message = "數據包含空值，請檢查查詢條件"
            else:
                error_code = "QUERY_ERROR"
                user_message = f"查詢執行失敗：{error_msg[:100]}"
        elif "timeout" in error_msg.lower():
            error_code = "QUERY_TIMEOUT"
            user_message = "查詢執行逾時，請減少查詢範圍"
        elif "connection" in error_msg.lower():
            error_code = "CONNECTION_ERROR"
            user_message = "資料庫連線失敗，請稍後重試"
        elif "memory" in error_msg.lower():
            error_code = "OUT_OF_MEMORY"
            user_message = "查詢記憶體不足：請減少查詢範圍"

        logger.error(f"Unexpected error: {error_msg}")
        return builder.build_error(
            error_code=error_code,
            message=user_message,
            exception=error_msg,
        )


@router.post("/v4/explain")
async def explain_query(
    request: ExecuteRequest, resolver: Resolver = Depends(get_resolver)
) -> dict:
    """
    解析查詢但不執行

    Args:
        request: 執行請求

    Returns:
        dict: 解析結果
    """
    logger.info(f"Received explain request: task_id={request.task_id}")

    try:
        # 解析但不執行
        resolve_result = resolver.resolve(request.task_data.nlq)

        return {
            "status": resolve_result["status"],
            "task_id": request.task_id,
            "sql": resolve_result.get("sql", ""),
            "state_history": resolve_result.get("state_history", []),
            "error": resolve_result.get("error"),
        }

    except Exception as e:
        logger.error(f"Explain error: {e}")
        return {"status": "error", "task_id": request.task_id, "error": str(e)}


@router.post("/v4/execute/stream")
async def execute_query_stream(request: ExecuteRequest):
    """
    SSE 版本的查詢執行端點

    通過 Server-Sent Events 即時回報各階段成果：
    - 已接收到請求
    - 已確認找到 Schema
    - 已產生 SQL
    - 正在執行查詢中
    - 已查詢完成
    - 已返回結果
    """

    # 獲取語言設定
    locale = get_locale(
        request.locale
        or (request.task_data.locale if request.task_data else None)
        or (
            request.task_data.options.locale
            if request.task_data and request.task_data.options
            else None
        ),
        fallback="zh-TW",
    )

    async def event_generator():
        builder = ResponseBuilder(task_id=request.task_id)
        builder.start_timing()

        try:
            # 階段 1: 接收到請求
            msg_request_received = t("REQUEST_RECEIVED", locale)
            yield f"data: {json.dumps({'stage': 'request_received', 'message': f'{msg_request_received}：{request.task_data.nlq}', 'data': {'nlq': request.task_data.nlq, 'locale': locale}}, ensure_ascii=False)}\n\n"

            # 獲取 Resolver
            resolver = get_resolver()

            # 解析 NLQ
            resolve_result = resolver.resolve(request.task_data.nlq)

            if resolve_result["status"] == "error":
                error_code = resolve_result.get("error_code", "INTERNAL_ERROR")
                message = resolve_result.get("message", t("INTENT_NOT_FOUND", locale))
                yield f"data: {json.dumps({'stage': 'error', 'message': f'{t("ERROR", locale)}：{message}', 'data': {'error_code': error_code, 'message': message, 'locale': locale}}, ensure_ascii=False)}\n\n"
                return

            # 階段 2: 確認 Schema
            schema_used = resolve_result.get("schema_used", "unknown")
            tables = resolve_result.get("tables_used", [])
            columns = resolve_result.get("columns_used", [])
            table_str = ", ".join(tables) if tables else schema_used
            column_str = ", ".join(columns[:5]) + ("..." if len(columns) > 5 else "")
            msg_schema_confirmed = t("SCHEMA_CONFIRMED", locale)
            yield f"data: {json.dumps({'stage': 'schema_confirmed', 'message': f'{msg_schema_confirmed}：{table_str}欄位：{column_str}', '，相關data': {'schema_used': schema_used, 'tables': tables, 'columns': columns, 'locale': locale}}, ensure_ascii=False)}\n\n"

            # 階段 3: SQL 已產生
            sql = resolve_result["sql"]
            intent = resolve_result.get("intent", "UNKNOWN")
            sql_preview = sql[:100] + "..." if len(sql) > 100 else sql
            msg_sql_generated = t("SQL_GENERATED", locale)
            yield f"data: {json.dumps({'stage': 'sql_generated', 'message': f'{msg_sql_generated}：{sql_preview}', 'data': {'sql': sql, 'intent': intent, 'locale': locale}}, ensure_ascii=False)}\n\n"

            # 執行前置驗證
            validator = PreValidator()
            entities = resolve_result.get("params", {})
            validation_result = await validator.validate(
                request.task_data.nlq,
                intent,
                entities,
                intent_confidence=resolve_result.get("confidence", 1.0),
            )

            if not validation_result.valid:
                errors = validation_result.errors
                first_error = errors[0] if errors else None
                if first_error:
                    error_code = first_error.code
                    user_message = first_error.message
                    yield f"data: {json.dumps({'stage': 'error', 'message': f'{t("ERROR", locale)}：{user_message}', 'data': {'status': 'error', 'error_code': error_code, 'message': user_message, 'locale': locale}}, ensure_ascii=False)}\n\n"
                    return

            # 獲取 Executor
            executor = get_executor()

            # 階段 4: 執行查詢
            timeout = request.task_data.options.timeout
            msg_query_executing = t("QUERY_EXECUTING", locale)
            yield f"data: {json.dumps({'stage': 'query_executing', 'message': f'{msg_query_executing}...（{t("timeout", locale)}：{timeout}s）', 'data': {'timeout': timeout, 'locale': locale}}, ensure_ascii=False)}\n\n"

            # 執行 SQL
            exec_result = executor.execute(sql, timeout)

            # 提取 columns
            result_data = exec_result.get("data", [])
            row_count = len(result_data)
            execution_time_ms = exec_result.get("execution_time_ms", 0)

            if result_data and len(result_data) > 0:
                columns = list(result_data[0].keys())
            else:
                columns = []

            # 建立分頁資訊（預設）
            page_size = (
                request.task_data.options.limit
                if request.task_data.options and request.task_data.options.limit
                else 100
            )
            pagination = {
                "page": 1,
                "page_size": page_size,
                "total_rows": row_count,
                "total_pages": (row_count + page_size - 1) // page_size if page_size > 0 else 1,
            }

            # Token 使用量（預設 - 實際應從 LLM 獲取）
            token_usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

            # 階段 5: 查詢完成
            msg_query_completed = t("QUERY_COMPLETED", locale)
            msg_execution_time = t("EXECUTION_TIME", locale, time=execution_time_ms)
            msg_rows = t("ROWS_RETURNED", locale, count=row_count)
            yield f"data: {json.dumps({'stage': 'query_completed', 'message': f'{msg_query_completed}...（{msg_execution_time}，{msg_rows}）', 'data': {'row_count': row_count, 'execution_time_ms': execution_time_ms, 'columns': columns, 'locale': locale}}, ensure_ascii=False)}\n\n"

            # 階段 6: 返回完整結果
            msg_result_ready = t("RESULT_READY", locale)
            msg_success = t("SUCCESS", locale)
            yield f"data: {json.dumps({'stage': 'result_ready', 'message': f'{msg_result_ready}：{msg_success}（{msg_rows}）', 'data': {'status': 'success', 'row_count': row_count, 'columns': columns, 'pagination': pagination, 'token_usage': token_usage, 'schema_used': schema_used, 'locale': locale}}, ensure_ascii=False)}\n\n"

            # 發送最終結果（包含完整數據）
            yield f"data: {json.dumps({'stage': 'final', 'message': '完成', 'data': {'status': 'success', 'row_count': row_count, 'columns': columns, 'pagination': pagination, 'token_usage': token_usage, 'schema_used': schema_used, 'locale': locale}}, ensure_ascii=False)}\n\n"

        except ResolverError as e:
            error_code = e.state.value if hasattr(e.state, "value") else "RESOLVER_ERROR"
            user_message = e.message or t("INTENT_NOT_FOUND", locale)
            yield f"data: {json.dumps({'stage': 'error', 'message': f'解析錯誤：{user_message}', 'data': {'status': 'error', 'error_code': error_code, 'message': user_message, 'locale': locale}}, ensure_ascii=False)}\n\n"

        except SQLExecutionError as e:
            error_code = "QUERY_TIMEOUT"
            error_msg = str(e)

            if "timeout" in error_msg.lower():
                error_code = "QUERY_TIMEOUT"
                user_message = t("QUERY_TIMEOUT", locale)
            elif "connection" in error_msg.lower():
                error_code = "CONNECTION_ERROR"
                user_message = t("CONNECTION_ERROR", locale)
            else:
                error_code = "QUERY_ERROR"
                user_message = t("QUERY_ERROR", locale)

            yield f"data: {json.dumps({'stage': 'error', 'message': f'執行錯誤：{user_message}', 'data': {'status': 'error', 'error_code': error_code, 'message': user_message, 'locale': locale}}, ensure_ascii=False)}\n\n"

        except Exception as e:
            error_msg = str(e)
            error_code = "INTERNAL_ERROR"
            user_message = error_msg

            if "DuckDB Execution Error" in error_msg:
                if "table with name" in error_msg.lower() and "does not exist" in error_msg.lower():
                    error_code = "SCHEMA_NOT_FOUND"
                    user_message = t("SCHEMA_NOT_FOUND", locale)
                elif "ambiguous reference" in error_msg.lower():
                    error_code = "AMBIGUOUS_REFERENCE"
                    user_message = t("AMBIGUOUS_REFERENCE", locale)
                elif "referenced column" in error_msg.lower():
                    error_code = "COLUMN_NOT_FOUND"
                    user_message = t("COLUMN_NOT_FOUND", locale)
                elif "binder error" in error_msg.lower():
                    error_code = "BINDER_ERROR"
                    user_message = t("BINDER_ERROR", locale)
                elif "out of memory" in error_msg.lower():
                    error_code = "OUT_OF_MEMORY"
                    user_message = t("OUT_OF_MEMORY", locale)
                else:
                    error_code = "QUERY_ERROR"
                    user_message = t("QUERY_ERROR", locale)
            elif "timeout" in error_msg.lower():
                error_code = "QUERY_TIMEOUT"
                user_message = t("QUERY_TIMEOUT", locale)
            elif "memory" in error_msg.lower():
                error_code = "OUT_OF_MEMORY"
                user_message = t("OUT_OF_MEMORY", locale)

            logger.error(f"SSE error: {error_msg}")
            msg_error = t("ERROR", locale)
            yield f"data: {json.dumps({'stage': 'error', 'message': f'{msg_error}：{user_message}', 'data': {'status': 'error', 'error_code': error_code, 'message': user_message, 'exception': error_msg, 'locale': locale}}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
