# 代碼功能說明: Data-Agent-JP API 路由
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Data-Agent-JP API 路由

端點：
- POST /api/v1/data-agent/jp/execute - 執行查詢
- GET /api/v1/data-agent/jp/health - 健康檢查
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends

from data_agent.services.schema_driven_query.models import (
    ExecuteRequest,
    ExecuteResponse,
    HealthResponse,
    QueryResult,
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


@router.get("/jp/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    健康檢查

    Returns:
        HealthResponse: 健康狀態
    """
    return HealthResponse(status="healthy", service="data-agent-jp", version="1.0.0")


@router.post("/jp/execute", response_model=ExecuteResponse)
async def execute_query(
    request: ExecuteRequest,
    resolver: Resolver = Depends(get_resolver),
    executor: SQLExecutor = Depends(get_executor),
) -> ExecuteResponse:
    """
    執行 Schema Driven Query

    Args:
        request: 執行請求

    Returns:
        ExecuteResponse: 執行結果
    """
    logger.info(f"Received query request: task_id={request.task_id}")

    try:
        # 1. 解析 NLQ
        resolve_result = resolver.resolve(request.task_data.nlq)

        if resolve_result["status"] == "error":
            return ExecuteResponse(
                status="error",
                task_id=request.task_id,
                error_code=resolve_result.get("error_code", "INTERNAL_ERROR"),
                message=resolve_result.get("message", "Unknown error"),
            )

        # 2. 執行 SQL
        sql = resolve_result["sql"]
        exec_result = executor.execute(sql, request.task_data.options.timeout)

        # 3. 返回結果
        result = QueryResult(
            sql=sql,
            data=exec_result["data"],
            row_count=exec_result["row_count"],
            execution_time_ms=exec_result["execution_time_ms"],
        )

        return ExecuteResponse(status="success", task_id=request.task_id, result=result)

    except ResolverError as e:
        logger.error(f"Resolver error: {e}")
        return ExecuteResponse(
            status="error",
            task_id=request.task_id,
            error_code=e.state.value if hasattr(e.state, "value") else "INTERNAL_ERROR",
            message=e.message,
        )

    except SQLExecutionError as e:
        logger.error(f"SQL execution error: {e}")
        return ExecuteResponse(
            status="error", task_id=request.task_id, error_code="CONNECTION_FAILED", message=str(e)
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return ExecuteResponse(
            status="error", task_id=request.task_id, error_code="INTERNAL_ERROR", message=str(e)
        )


@router.post("/jp/explain")
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
