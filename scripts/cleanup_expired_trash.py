# 代碼功能說明: 定時清理過期 Trash 任務
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""定時清理過期 Trash 任務 - 永久刪除已超過 7 天的任務

此腳本用於定時清理已軟刪除（Soft Delete）超過 7 天的任務。
可以通過以下方式執行：
1. 直接運行：python scripts/cleanup_expired_trash.py
2. 添加到 cron job：0 2 * * * python /path/to/cleanup_expired_trash.py
3. 添加到 RQ scheduler
"""

from datetime import datetime, timedelta
from typing import Any, Dict

import structlog

from database.arangodb import ArangoDBClient
from storage.file_storage import create_storage_from_config
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "user_tasks"


def cleanup_expired_trash_tasks(
    max_age_days: int = 7,
    batch_size: int = 100,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    清理過期的 Trash 任務（永久刪除）

    修改時間：2026-01-21 - 添加定時清理功能

    Args:
        max_age_days: 最大保留天數（默認 7 天）
        batch_size: 每批處理的任務數量
        dry_run: 演練模式（True = 不實際刪除，只記錄日誌）

    Returns:
        清理結果統計
    """
    logger.info(
        "Starting expired trash cleanup",
        max_age_days=max_age_days,
        batch_size=batch_size,
        dry_run=dry_run,
    )

    result: Dict[str, Any] = {
        "started_at": datetime.utcnow().isoformat(),
        "max_age_days": max_age_days,
        "batch_size": batch_size,
        "dry_run": dry_run,
        "tasks_scanned": 0,
        "tasks_to_delete": 0,
        "tasks_deleted": 0,
        "tasks_failed": 0,
        "errors": [],
        "completed_at": None,
    }

    try:
        # 連接 ArangoDB
        arangodb_client = ArangoDBClient()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = arangodb_client.db.collection(COLLECTION_NAME)

        # 計算截止時間
        cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
        cutoff_iso = cutoff_iso = cutoff_date.isoformat()

        logger.info("Cleanup cutoff date", cutoff=cutoff_iso)

        # 查詢需要清理的任務
        # 條件：task_status = "trash" AND permanent_delete_at < now
        query = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER doc.task_status == "trash"
        FILTER doc.permanent_delete_at != null
        FILTER doc.permanent_delete_at < @cutoff
        LIMIT @batch_size
        RETURN doc
        """

        cursor = arangodb_client.db.aql.execute(
            query,
            bindvars={
                "cutoff": cutoff_iso,
                "batch_size": batch_size,
            },
        )

        expired_tasks = list(cursor)
        result["tasks_scanned"] = len(expired_tasks)
        result["tasks_to_delete"] = len(expired_tasks)

        logger.info(
            "Found expired tasks to delete",
            count=len(expired_tasks),
            dry_run=dry_run,
        )

        # 初始化服務（用於清理關聯數據）
        from services.api.services.deletion_rollback_manager import DeletionRollbackManager
        from services.api.services.file_metadata_service import FileMetadataService
        from services.api.services.folder_metadata_service import get_folder_metadata_service
        from services.api.services.qdrant_vector_store_service import (
            get_qdrant_vector_store_service,
        )

        file_metadata_service = FileMetadataService()
        vector_store_service = get_qdrant_vector_store_service()
        folder_service = get_folder_metadata_service()
        storage_config = get_config_section("storage")
        storage = create_storage_from_config(storage_config)

        # 處理每個過期任務
        for task_doc in expired_tasks:
            task_id = task_doc.get("task_id") or task_doc.get("_key")
            user_id = task_doc.get("user_id")

            if not task_id or not user_id:
                result["errors"].append(f"Task missing task_id or user_id: {task_doc.get('_key')}")
                result["tasks_failed"] += 1
                continue

            logger.info(
                "Processing expired task",
                task_id=task_id,
                user_id=user_id,
                permanent_delete_at=task_doc.get("permanent_delete_at"),
                dry_run=dry_run,
            )

            if dry_run:
                # 演練模式，跳過實際刪除
                continue

            try:
                # 創建回滾管理器
                rollback_manager = DeletionRollbackManager(
                    task_id=task_id,
                    user_id=user_id,
                    vector_store_service=vector_store_service,
                    file_metadata_service=file_metadata_service,
                    folder_metadata_service=folder_service,
                    storage=storage,
                    arangodb_client=arangodb_client,
                )

                # 清理任務下的文件
                task_files = file_metadata_service.list(
                    user_id=user_id,
                    task_id=task_id,
                    limit=1000,
                )

                for file_metadata in task_files:
                    file_id = file_metadata.file_id
                    storage_path = getattr(file_metadata, "storage_path", None)

                    try:
                        rollback_manager.delete_vector_with_rollback(file_id, storage_path)
                        rollback_manager.delete_kg_entities_with_rollback(file_id)
                        rollback_manager.delete_kg_relations_with_rollback(file_id)
                        rollback_manager.delete_metadata_with_rollback(file_id)
                        rollback_manager.delete_file_with_rollback(file_id, storage_path)
                    except Exception as e:
                        logger.warning(
                            "Failed to delete file data",
                            task_id=task_id,
                            file_id=file_id,
                            error=str(e),
                        )

                # 清理任務下的資料夾
                try:
                    folders = folder_service.list(task_id=task_id)
                    for folder in folders:
                        folder_id = folder.get("folder_id") or folder.get("_key")
                        if folder_id:
                            rollback_manager.delete_folder_with_rollback(folder_id)
                except Exception as e:
                    logger.warning(
                        "Failed to delete folder data",
                        task_id=task_id,
                        error=str(e),
                    )

                # 完成事務
                transaction = rollback_manager.complete()

                # 永久刪除任務文檔
                doc_key = task_doc.get("_key")
                if doc_key:
                    collection.delete(doc_key)

                result["tasks_deleted"] += 1
                logger.info(
                    "Task permanently deleted",
                    task_id=task_id,
                    user_id=user_id,
                )

            except Exception as e:
                error_msg = f"Failed to delete task {task_id}: {str(e)}"
                result["errors"].append(error_msg)
                result["tasks_failed"] += 1
                logger.error(
                    "Failed to delete expired task",
                    task_id=task_id,
                    error=str(e),
                    exc_info=True,
                )

        # 完成
        result["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "Expired trash cleanup completed",
            tasks_scanned=result["tasks_scanned"],
            tasks_deleted=result["tasks_deleted"],
            tasks_failed=result["tasks_failed"],
            dry_run=dry_run,
        )

        return result

    except Exception as e:
        result["completed_at"] = datetime.utcnow().isoformat()
        result["errors"].append(f"Cleanup failed: {str(e)}")
        logger.error(
            "Expired trash cleanup failed",
            error=str(e),
            exc_info=True,
        )
        return result


def enqueue_cleanup_job(
    max_age_days: int = 7,
    batch_size: int = 100,
) -> str:
    """
    將清理任務加入 RQ 隊列

    Args:
        max_age_days: 最大保留天數
        batch_size: 每批處理的任務數量

    Returns:
        作業 ID
    """
    from database.rq.queue import TASK_DELETION_QUEUE, get_task_queue

    queue = get_task_queue(TASK_DELETION_QUEUE)

    job = queue.enqueue(
        cleanup_expired_trash_tasks,
        max_age_days=max_age_days,
        batch_size=batch_size,
        dry_run=False,
        job_timeout="30m",  # 30 分鐘超時
        result_ttl=3600,  # 結果保存 1 小時
    )

    logger.info(
        "Cleanup job enqueued",
        job_id=job.get_id(),
        max_age_days=max_age_days,
        batch_size=batch_size,
    )

    return job.get_id()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="清理過期的 Trash 任務")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="最大保留天數（默認 7 天）",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=100,
        help="每批處理的任務數量（默認 100）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演練模式（不實際刪除）",
    )
    parser.add_argument(
        "--enqueue",
        action="store_true",
        help="將任務加入 RQ 隊列（後台執行）",
    )

    args = parser.parse_args()

    if args.enqueue:
        job_id = enqueue_cleanup_job(
            max_age_days=args.days,
            batch_size=args.batch,
        )
        print(f"Cleanup job enqueued: {job_id}")
    else:
        result = cleanup_expired_trash_tasks(
            max_age_days=args.days,
            batch_size=args.batch,
            dry_run=args.dry_run,
        )

        print("\n=== 清理結果 ===")
        print(f"掃描任務數: {result['tasks_scanned']}")
        print(f"待刪除任務數: {result['tasks_to_delete']}")
        print(f"已刪除任務數: {result['tasks_deleted']}")
        print(f"失敗任務數: {result['tasks_failed']}")
        print(f"開始時間: {result['started_at']}")
        print(f"完成時間: {result['completed_at']}")

        if result["errors"]:
            print("\n錯誤:")
            for error in result["errors"][:10]:  # 只顯示前 10 個錯誤
                print(f"  - {error}")
