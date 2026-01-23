# 代碼功能說明: RQ 隊列監控 API
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ 隊列監控 API - 提供隊列狀態查詢接口"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from database.rq.monitor import (
    get_all_queues,
    get_all_queues_stats,
    get_queue_jobs,
    get_queue_stats,
    get_workers_info,
)
from system.security.dependencies import get_current_user
from system.security.models import User

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
        logger.error("批量提交任務失敗", error=str(e))
        return APIResponse.error(
            message=f"批量提交任務失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/bulk-retry-failed")
async def bulk_retry_failed_tasks(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    重試所有失敗的任務

    此端點用於批量重試指定任務中所有失敗的子任務。
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
    job_status: Optional[str] = Query(  # 重命名為 job_status 避免與 status 模塊衝突
        None, description="任務狀態 (queued/started/finished/failed)", alias="status"
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
        jobs = get_queue_jobs(queue_name, status=job_status, limit=limit)
        return APIResponse.success(
            data={"jobs": jobs, "count": len(jobs)},
            message="任務列表獲取成功",
        )
    except Exception as e:
        logger.error(
            "Failed to list queue jobs",
            queue_name=queue_name,
            status=job_status,
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


@router.post("/batch-upload")
async def batch_upload_files(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """批量提交文件處理任務到 Worker 隊列。

    Request Body:
        {
            "file_ids": ["file_id_1", "file_id_2", ...],
            "task_id": "task_id",  // 可選
            "options": {
                "rechunk": false,      // 是否重新分塊
                "vectorize": true,     // 是否向量化
                "extract_kg": true     // 是否提取知識圖譜
            }
        }

    Returns:
        提交結果
    """
    try:
        body = await request.json()
        file_ids = body.get("file_ids", [])

        if not file_ids:
            return APIResponse.error(
                message="file_ids 列表不能為空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        from database.rq.queue import FILE_PROCESSING_QUEUE, get_task_queue
        from workers.tasks import process_file_chunking_and_vectorization_task

        if not isinstance(file_ids, list):
            return APIResponse.error(
                message="file_ids 必須是陣列",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        import os

        from arango.client import ArangoClient

        arango_host = os.getenv("ARANGODB_HOST", "localhost")
        arango_port = int(os.getenv("ARANGODB_PORT", "8529"))
        arango_db = "ai_box_kg"
        arango_user = os.getenv("ARANGODB_USERNAME", "root")
        arango_pass = os.getenv("ARANGODB_PASSWORD", "changeme")

        arango_client = ArangoClient(hosts=f"http://{arango_host}:{arango_port}")
        db = arango_client.db(arango_db, username=arango_user, password=arango_pass)

        results = []
        queue = get_task_queue(FILE_PROCESSING_QUEUE)

        for file_id in file_ids:
            try:
                file_metadata = db.collection("file_metadata").get(file_id)

                if not file_metadata:
                    results.append(
                        {
                            "file_id": file_id,
                            "status": "error",
                            "error": "文件元數據不存在",
                        }
                    )
                    continue

                file_path = file_metadata.get("storage_path")
                file_type = file_metadata.get("file_type")

                job_timeout = 3600
                job = queue.enqueue(
                    process_file_chunking_and_vectorization_task,
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_type,
                    user_id=current_user.user_id,
                    job_timeout=job_timeout,
                )

                results.append(
                    {
                        "file_id": file_id,
                        "status": "queued",
                        "job_id": job.id,
                        "queue": FILE_PROCESSING_QUEUE,
                    }
                )

            except Exception as e:
                logger.error("提交任務失敗", file_id=file_id, error=str(e))
                results.append(
                    {
                        "file_id": file_id,
                        "status": "error",
                        "error": str(e),
                    }
                )

        return APIResponse.success(
            data={
                "submitted": len([r for r in results if r["status"] == "queued"]),
                "failed": len([r for r in results if r["status"] == "error"]),
                "results": results,
            },
            message=f"成功提交 {len([r for r in results if r['status'] == 'queued'])} 個任務",
        )

    except Exception as e:
        logger.error("批量提交任務失敗", error=str(e))
        return APIResponse.error(
            message=f"批量提交任務失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
