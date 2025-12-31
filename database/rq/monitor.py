# 代碼功能說明: RQ 隊列監控工具
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-13 18:28:38 (UTC+8)

"""RQ 隊列監控工具 - 提供隊列狀態查詢和統計功能"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import structlog

from database.rq.queue import get_redis_connection

logger = structlog.get_logger(__name__)

if TYPE_CHECKING:
    from rq import Queue, Worker
    from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry


def _require_rq() -> Tuple[
    "type[Queue]",
    "type[Worker]",
    "type[StartedJobRegistry]",
    "type[FinishedJobRegistry]",
    "type[FailedJobRegistry]",
]:
    """確保 rq 可用；否則拋出可讀錯誤。"""
    try:
        from rq import Queue, Worker
        from rq.registry import FailedJobRegistry, FinishedJobRegistry, StartedJobRegistry

        return Queue, Worker, StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry
    except ImportError as exc:
        raise RuntimeError("RQ is not installed. Please install it first: pip install rq") from exc


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
        Queue, _, StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry = _require_rq()
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
        _, Worker, _, _, _ = _require_rq()
        redis_conn = get_redis_connection()
        workers = Worker.all(connection=redis_conn)

        workers_info = []
        for worker in workers:
            worker_info = {
                "name": worker.name,
                "state": worker.state,
                "queues": worker.queue_names(),
                "current_job_id": worker.current_job.id if worker.current_job else None,
                "birth_date": (worker.birth_date.isoformat() if worker.birth_date else None),
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
        Queue, _, _, _, _ = _require_rq()
        redis_conn = get_redis_connection()
        queue = Queue(queue_name, connection=redis_conn)

        jobs_info = []

        if status is None or status == "queued":
            # 獲取等待中的任務
            job_ids = queue.get_job_ids(0, limit - 1)
            for job_id in job_ids:
                try:
                    job = queue.fetch_job(job_id)
                    if job:
                        # 修改時間：2025-12-12 - 安全處理 job.args 和 kwargs，避免編碼錯誤
                        args_str = None
                        try:
                            if job.args:
                                args_str = str(job.args)[:200] if job.args else None
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            args_str = repr(job.args)[:200] if job.args else None

                        # 處理 kwargs（關鍵字參數）
                        kwargs_str = None
                        kwargs_dict = {}
                        try:
                            if hasattr(job, "kwargs") and job.kwargs:
                                kwargs_dict = dict(job.kwargs) if job.kwargs else {}
                                kwargs_str = str(kwargs_dict)[:300]
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            try:
                                kwargs_str = (
                                    repr(job.kwargs)[:300]
                                    if hasattr(job, "kwargs") and job.kwargs
                                    else None
                                )
                            except Exception:
                                kwargs_str = None

                        # 修改時間：2025-12-12 - 將 JobStatus 枚舉轉換為字符串
                        job_status = job.get_status()
                        if hasattr(job_status, "value"):
                            job_status = job_status.value
                        elif hasattr(job_status, "name"):
                            job_status = job_status.name.lower()

                        # 提取關鍵信息（file_id, user_id 等）
                        file_id = kwargs_dict.get("file_id") if kwargs_dict else None
                        user_id = kwargs_dict.get("user_id") if kwargs_dict else None
                        file_path = kwargs_dict.get("file_path") if kwargs_dict else None

                        jobs_info.append(
                            {
                                "job_id": job.id,
                                "status": job_status,
                                "created_at": (
                                    job.created_at.isoformat() if job.created_at else None
                                ),
                                "func_name": job.func_name,
                                "args": args_str,
                                "kwargs": kwargs_str,
                                "file_id": file_id,
                                "user_id": user_id,
                                "file_path": file_path,
                            }
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch job",
                        job_id=job_id,
                        error=str(e),
                    )
                    continue

        if status is None or status == "started":
            # 獲取執行中的任務
            started_registry = StartedJobRegistry(queue_name, connection=redis_conn)
            job_ids = started_registry.get_job_ids(0, limit - 1)
            for job_id in job_ids:
                try:
                    job = queue.fetch_job(job_id)
                    if job:
                        # 修改時間：2025-12-12 - 將 JobStatus 枚舉轉換為字符串
                        job_status = job.get_status()
                        if hasattr(job_status, "value"):
                            job_status = job_status.value
                        elif hasattr(job_status, "name"):
                            job_status = job_status.name.lower()

                        jobs_info.append(
                            {
                                "job_id": job.id,
                                "status": job_status,
                                "started_at": (
                                    job.started_at.isoformat() if job.started_at else None
                                ),
                                "func_name": job.func_name,
                            }
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch started job",
                        job_id=job_id,
                        error=str(e),
                    )
                    continue

        if status is None or status == "failed":
            # 獲取失敗的任務
            failed_registry = FailedJobRegistry(queue_name, connection=redis_conn)
            job_ids = failed_registry.get_job_ids(0, limit - 1)
            for job_id in job_ids:
                try:
                    job = queue.fetch_job(job_id)
                    if job:
                        # 修改時間：2025-12-12 - 安全處理 exc_info，避免編碼錯誤
                        exc_info_str = None
                        try:
                            exc_info_str = str(job.exc_info)[:200] if job.exc_info else None
                        except (UnicodeDecodeError, UnicodeEncodeError):
                            exc_info_str = repr(job.exc_info)[:200] if job.exc_info else None

                        # 修改時間：2025-12-12 - 將 JobStatus 枚舉轉換為字符串
                        job_status = job.get_status()
                        if hasattr(job_status, "value"):
                            job_status = job_status.value
                        elif hasattr(job_status, "name"):
                            job_status = job_status.name.lower()

                        jobs_info.append(
                            {
                                "job_id": job.id,
                                "status": job_status,
                                "ended_at": (job.ended_at.isoformat() if job.ended_at else None),
                                "exc_info": exc_info_str,
                                "func_name": job.func_name,
                            }
                        )
                except Exception as e:
                    logger.warning(
                        "Failed to fetch failed job",
                        job_id=job_id,
                        error=str(e),
                    )
                    continue

        return jobs_info[:limit]
    except Exception as e:
        logger.error(
            "Failed to get queue jobs",
            queue_name=queue_name,
            status=status,
            error=str(e),
        )
        return []
