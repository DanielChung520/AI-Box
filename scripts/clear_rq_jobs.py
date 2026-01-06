# 代碼功能說明: 清理 RQ 隊列中的舊任務
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""清理 RQ 隊列中的舊任務（排隊中、執行中、已調度、已延遲）"""

import sys
import os
from typing import List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from rq import Queue
    from database.rq.queue import (
        get_redis_connection,
        KG_EXTRACTION_QUEUE,
        VECTORIZATION_QUEUE,
        FILE_PROCESSING_QUEUE,
        GENAI_CHAT_QUEUE,
    )
except ImportError as e:
    print(f"❌ 導入失敗: {e}")
    print("請確保已安裝 rq: pip install rq")
    sys.exit(1)


def clear_queue_jobs(queue_name: str, clear_failed: bool = False) -> dict:
    """清理隊列中的任務"""
    redis_conn = get_redis_connection()
    queue = Queue(queue_name, connection=redis_conn)

    result = {
        "queue_name": queue_name,
        "cleared": {
            "queued": 0,
            "started": 0,
            "scheduled": 0,
            "deferred": 0,
            "failed": 0,
        },
    }

    # 清理排隊中的任務
    job_ids = queue.get_job_ids(0, -1)
    for job_id in job_ids:
        try:
            job = queue.fetch_job(job_id)
            if job:
                job.delete()
                result["cleared"]["queued"] += 1
        except Exception as e:
            print(f"  警告: 清理排隊任務 {job_id} 失敗: {e}")

    # 清理執行中的任務
    started_job_ids = queue.started_job_registry.get_job_ids()
    for job_id in started_job_ids:
        try:
            job = queue.fetch_job(job_id)
            if job:
                job.cancel()
                job.delete()
                result["cleared"]["started"] += 1
        except Exception as e:
            print(f"  警告: 清理執行中任務 {job_id} 失敗: {e}")

    # 清理已調度的任務
    scheduled_job_ids = queue.scheduled_job_registry.get_job_ids()
    for job_id in scheduled_job_ids:
        try:
            job = queue.fetch_job(job_id)
            if job:
                job.delete()
                result["cleared"]["scheduled"] += 1
        except Exception as e:
            print(f"  警告: 清理已調度任務 {job_id} 失敗: {e}")

    # 清理已延遲的任務
    deferred_job_ids = queue.deferred_job_registry.get_job_ids()
    for job_id in deferred_job_ids:
        try:
            job = queue.fetch_job(job_id)
            if job:
                job.delete()
                result["cleared"]["deferred"] += 1
        except Exception as e:
            print(f"  警告: 清理已延遲任務 {job_id} 失敗: {e}")

    # 清理失敗的任務（可選）
    if clear_failed:
        failed_job_ids = queue.failed_job_registry.get_job_ids()
        for job_id in failed_job_ids:
            try:
                job = queue.fetch_job(job_id)
                if job:
                    job.delete()
                    result["cleared"]["failed"] += 1
            except Exception as e:
                print(f"  警告: 清理失敗任務 {job_id} 失敗: {e}")

    return result


def clear_all_queues(queue_names: Optional[List[str]] = None, clear_failed: bool = False) -> dict:
    """清理所有隊列的任務"""
    if queue_names is None:
        queue_names = [
            KG_EXTRACTION_QUEUE,
            VECTORIZATION_QUEUE,
            FILE_PROCESSING_QUEUE,
            GENAI_CHAT_QUEUE,
        ]

    print("=" * 80)
    print("清理 RQ 隊列任務")
    print("=" * 80)
    print()

    all_results = {}
    total_cleared = 0

    for queue_name in queue_names:
        print(f"清理隊列: {queue_name}")
        try:
            result = clear_queue_jobs(queue_name, clear_failed=clear_failed)
            all_results[queue_name] = result

            queue_total = sum(result["cleared"].values())
            total_cleared += queue_total

            if queue_total > 0:
                print(f"  ✅ 已清理:")
                for status, count in result["cleared"].items():
                    if count > 0:
                        print(f"    - {status}: {count} 個")
            else:
                print(f"  ℹ️  隊列為空，無需清理")
        except Exception as e:
            print(f"  ❌ 清理失敗: {e}")
            all_results[queue_name] = {"error": str(e)}

        print()

    print("=" * 80)
    print(f"總共清理了 {total_cleared} 個任務")
    print("=" * 80)

    return all_results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理 RQ 隊列中的舊任務")
    parser.add_argument("--queue", help="要清理的隊列名稱（可指定多個，用逗號分隔）", default=None)
    parser.add_argument("--all", action="store_true", help="清理所有隊列")
    parser.add_argument("--clear-failed", action="store_true", help="同時清理失敗的任務（默認只清理活躍任務）")
    args = parser.parse_args()

    queue_names = None
    if args.queue:
        queue_names = [q.strip() for q in args.queue.split(",")]
    elif args.all:
        queue_names = None  # 清理所有隊列
    else:
        # 默認清理主要隊列
        queue_names = [KG_EXTRACTION_QUEUE, VECTORIZATION_QUEUE, FILE_PROCESSING_QUEUE]

    clear_all_queues(queue_names=queue_names, clear_failed=args.clear_failed)
