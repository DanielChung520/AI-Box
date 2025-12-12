# 代碼功能說明: RQ 隊列監控 API
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ 隊列監控 API - 提供隊列狀態查詢接口"""

from typing import Optional
from fastapi import APIRouter, Query, Depends, status
from fastapi.responses import JSONResponse
import structlog

from api.core.response import APIResponse
from system.security.dependencies import get_current_user
from system.security.models import User
from database.rq.monitor import (
    get_all_queues,
    get_queue_stats,
    get_all_queues_stats,
    get_workers_info,
    get_queue_jobs,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/rq", tags=["RQ Monitor"])


@router.get("/queues")
async def list_queues(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取所有隊列列表。

    Returns:
        隊列名稱列表
    """
    try:
        queues = get_all_queues()
        return APIResponse.success(
            data={"queues": queues, "count": len(queues)},
            message="隊列列表獲取成功",
        )
    except Exception as e:
        logger.error("Failed to list queues", error=str(e))
        return APIResponse.error(
            message=f"獲取隊列列表失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/queues/stats")
async def get_queues_stats(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取所有隊列的統計信息。

    Returns:
        所有隊列的統計信息
    """
    try:
        stats = get_all_queues_stats()
        return APIResponse.success(
            data={"queues": stats},
            message="隊列統計信息獲取成功",
        )
    except Exception as e:
        logger.error("Failed to get queues stats", error=str(e))
        return APIResponse.error(
            message=f"獲取隊列統計信息失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/queues/{queue_name}/stats")
async def get_queue_statistics(
    queue_name: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取指定隊列的統計信息。

    Args:
        queue_name: 隊列名稱

    Returns:
        隊列統計信息
    """
    try:
        stats = get_queue_stats(queue_name)
        if "error" in stats:
            return APIResponse.error(
                message=f"獲取隊列統計信息失敗: {stats['error']}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return APIResponse.success(
            data=stats,
            message="隊列統計信息獲取成功",
        )
    except Exception as e:
        logger.error("Failed to get queue stats", queue_name=queue_name, error=str(e))
        return APIResponse.error(
            message=f"獲取隊列統計信息失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/queues/{queue_name}/jobs")
async def list_queue_jobs(
    queue_name: str,
    status: Optional[str] = Query(
        None, description="任務狀態 (queued/started/finished/failed)"
    ),
    limit: int = Query(10, ge=1, le=100, description="返回任務數量限制"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取隊列中的任務列表。

    Args:
        queue_name: 隊列名稱
        status: 任務狀態過濾
        limit: 返回任務數量限制

    Returns:
        任務列表
    """
    try:
        jobs = get_queue_jobs(queue_name, status=status, limit=limit)
        return APIResponse.success(
            data={"jobs": jobs, "count": len(jobs)},
            message="任務列表獲取成功",
        )
    except Exception as e:
        logger.error(
            "Failed to list queue jobs",
            queue_name=queue_name,
            status=status,
            error=str(e),
        )
        return APIResponse.error(
            message=f"獲取任務列表失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/workers")
async def list_workers(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取所有 Worker 信息。

    Returns:
        Worker 信息列表
    """
    try:
        workers = get_workers_info()
        return APIResponse.success(
            data={"workers": workers, "count": len(workers)},
            message="Worker 信息獲取成功",
        )
    except Exception as e:
        logger.error("Failed to list workers", error=str(e))
        return APIResponse.error(
            message=f"獲取 Worker 信息失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
