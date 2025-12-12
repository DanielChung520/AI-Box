# 代碼功能說明: RQ 隊列監控工具
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

"""RQ 隊列監控工具 - 提供隊列狀態查詢和統計功能"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import structlog
from rq import Queue, Worker
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry

from database.rq.queue import get_redis_connection

logger = structlog.get_logger(__name__)


def get_all_queues() -> List[str]:
    """獲取所有隊列名稱。

    Returns:
        隊列名稱列表
    """
    try:
        redis_conn = get_redis_connection()
        # RQ 使用 Redis key 格式: rq:queue:{queue_name}
        queue_keys = redis_conn.keys("rq:queue:*")
        queue_names = []
        for key in queue_keys:
            if isinstance(key, str):
                queue_name = key.replace("rq:queue:", "")
            else:
                queue_name = key.decode().replace("rq:queue:", "")
            queue_names.append(queue_name)
        return sorted(queue_names)
    except Exception as e:
        logger.error("Failed to get all queues", error=str(e))
        return []


def get_queue_stats(queue_name: str) -> Dict[str, Any]:
    """獲取隊列統計信息。

    Args:
        queue_name: 隊列名稱

    Returns:
        隊列統計信息字典
    """
    try:
        redis_conn = get_redis_connection()
        queue = Queue(queue_name, connection=redis_conn)

        # 獲取各個狀態的任務數量
        queued = len(queue)
        started_registry = StartedJobRegistry(queue_name, connection=redis_conn)
        finished_registry = FinishedJobRegistry(queue_name, connection=redis_conn)
        failed_registry = FailedJobRegistry(queue_name, connection=redis_conn)

        started = len(started_registry)
        finished = len(finished_registry)
        failed = len(failed_registry)

        return {
            "queue_name": queue_name,
            "queued": queued,
            "started": started,
            "finished": finished,
            "failed": failed,
            "total": queued + started + finished + failed,
        }
    except Exception as e:
        logger.error("Failed to get queue stats", queue_name=queue_name, error=str(e))
        return {
            "queue_name": queue_name,
            "error": str(e),
        }


def get_all_queues_stats() -> Dict[str, Dict[str, Any]]:
    """獲取所有隊列的統計信息。

    Returns:
        隊列統計信息字典，key 為隊列名稱
    """
    queue_names = get_all_queues()
    stats = {}
    for queue_name in queue_names:
        stats[queue_name] = get_queue_stats(queue_name)
    return stats


def get_workers_info() -> List[Dict[str, Any]]:
    """獲取所有 Worker 的信息。

    Returns:
        Worker 信息列表
    """
    try:
        redis_conn = get_redis_connection()
        workers = Worker.all(connection=redis_conn)

        workers_info = []
        for worker in workers:
            worker_info = {
                "name": worker.name,
                "state": worker.state,
                "queues": worker.queue_names(),
                "current_job_id": worker.current_job.id if worker.current_job else None,
                "birth_date": (
                    worker.birth_date.isoformat() if worker.birth_date else None
                ),
            }
            workers_info.append(worker_info)

        return workers_info
    except Exception as e:
        logger.error("Failed to get workers info", error=str(e))
        return []


def get_queue_jobs(
    queue_name: str,
    status: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """獲取隊列中的任務列表。

    Args:
        queue_name: 隊列名稱
        status: 任務狀態 ('queued', 'started', 'finished', 'failed')，None 表示所有狀態
        limit: 返回任務數量限制

    Returns:
        任務信息列表
    """
    try:
        redis_conn = get_redis_connection()
        queue = Queue(queue_name, connection=redis_conn)

        jobs_info = []

        if status is None or status == "queued":
            # 獲取等待中的任務
            job_ids = queue.get_job_ids(0, limit - 1)
            for job_id in job_ids:
                job = queue.fetch_job(job_id)
                if job:
                    jobs_info.append(
                        {
                            "job_id": job.id,
                            "status": job.get_status(),
                            "created_at": (
                                job.created_at.isoformat() if job.created_at else None
                            ),
                            "func_name": job.func_name,
                            "args": str(job.args)[:100],  # 限制長度
                        }
                    )

        if status is None or status == "started":
            # 獲取執行中的任務
            started_registry = StartedJobRegistry(queue_name, connection=redis_conn)
            job_ids = started_registry.get_job_ids(0, limit - 1)
            for job_id in job_ids:
                job = queue.fetch_job(job_id)
                if job:
                    jobs_info.append(
                        {
                            "job_id": job.id,
                            "status": job.get_status(),
                            "started_at": (
                                job.started_at.isoformat() if job.started_at else None
                            ),
                            "func_name": job.func_name,
                        }
                    )

        if status is None or status == "failed":
            # 獲取失敗的任務
            failed_registry = FailedJobRegistry(queue_name, connection=redis_conn)
            job_ids = failed_registry.get_job_ids(0, limit - 1)
            for job_id in job_ids:
                job = queue.fetch_job(job_id)
                if job:
                    jobs_info.append(
                        {
                            "job_id": job.id,
                            "status": job.get_status(),
                            "ended_at": (
                                job.ended_at.isoformat() if job.ended_at else None
                            ),
                            "exc_info": (
                                str(job.exc_info)[:200] if job.exc_info else None
                            ),
                            "func_name": job.func_name,
                        }
                    )

        return jobs_info[:limit]
    except Exception as e:
        logger.error(
            "Failed to get queue jobs",
            queue_name=queue_name,
            status=status,
            error=str(e),
        )
        return []
