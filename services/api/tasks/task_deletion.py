# 代碼功能說明: 任務刪除異步作業
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""任務刪除異步作業 - 通過 RQ 隊列執行任務刪除

修改時間：2026-01-21 - 添加 Soft Delete 機制

新流程：
1. 先標記任務為 soft-deleted（deleted_at, permanent_delete_at）
2. 在後台執行實際清理
3. 清理完成後，任務會在 7 天後自動被定時任務永久刪除
"""

from datetime import datetime
from typing import Any, Dict

import structlog

from database.arangodb import ArangoDBClient
from database.rq.queue import TASK_DELETION_QUEUE, get_task_queue
from services.api.services.deletion_rollback_manager import DeletionRollbackManager
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.folder_metadata_service import get_folder_metadata_service
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service
from services.api.services.user_task_service import UserTaskService
from storage.file_storage import create_storage_from_config
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)


def execute_task_deletion(
    task_id: str,
    user_id: str,
    skip_soft_delete: bool = False,
) -> Dict[str, Any]:
    """
    執行任務刪除的後台作業

    修改時間：2026-01-21 - 添加 Soft Delete 機制

    Args:
        task_id: 任務 ID
        user_id: 用戶 ID
        skip_soft_delete: 是否跳過 Soft Delete 標記（用於直接永久刪除）

    Returns:
        刪除結果字典
    """
    logger.info("Starting task deletion background job", task_id=task_id, user_id=user_id)

    result: Dict[str, Any] = {
        "task_id": task_id,
        "user_id": user_id,
        "started_at": datetime.utcnow().isoformat(),
        "status": "in_progress",
        "files_deleted": 0,
        "folders_deleted": 0,
        "vectors_deleted": 0,
        "kg_deleted": False,
        "errors": [],
        "completed_at": None,
    }

    try:
        arangodb_client = ArangoDBClient()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        task_service = UserTaskService(client=arangodb_client)
        collection = arangodb_client.db.collection("user_tasks")
        doc = None

        for doc_key in [f"{user_id}_{task_id}", task_id]:
            doc = collection.get(doc_key)
            if doc:
                break

        if doc is None:
            result["status"] = "failed"
            result["errors"].append("Task not found")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result

        # 確保任務屬於當前用戶
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != user_id:
            result["status"] = "failed"
            result["errors"].append("Task not found or access denied")
            result["completed_at"] = datetime.utcnow().isoformat()
            return result

        # 修改時間：2026-01-21 - 如果任務還未標記為 Soft Delete，先進行標記
        if not skip_soft_delete:
            if doc.get("deleted_at") is None:
                logger.info("Soft deleting task before cleanup", task_id=task_id)
                soft_delete_result = task_service.soft_delete(user_id=user_id, task_id=task_id)
                if not soft_delete_result.get("success"):
                    result["status"] = "failed"
                    result["errors"].append(
                        f"Soft delete failed: {soft_delete_result.get('error')}"
                    )
                    result["completed_at"] = datetime.utcnow().isoformat()
                    return result
                result["soft_delete"] = soft_delete_result
            else:
                logger.info("Task already soft-deleted, proceeding with cleanup", task_id=task_id)

        # 初始化服務
        file_metadata_service = FileMetadataService()
        vector_store_service = get_qdrant_vector_store_service()
        folder_service = get_folder_metadata_service()
        storage_config = get_config_section("storage")
        storage = create_storage_from_config(storage_config)

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

        # 獲取任務下的所有文件
        task_files = file_metadata_service.list(
            user_id=user_id,
            task_id=task_id,
            limit=1000,
        )

        # 刪除每個文件的所有關聯數據
        for file_metadata in task_files:
            file_id = file_metadata.file_id
            storage_path = getattr(file_metadata, "storage_path", None)

            try:
                # 刪除向量
                rollback_manager.delete_vector_with_rollback(file_id, storage_path)

                # 刪除知識圖譜實體
                rollback_manager.delete_kg_entities_with_rollback(file_id)

                # 刪除知識圖譜關係
                rollback_manager.delete_kg_relations_with_rollback(file_id)

                # 刪除元數據
                rollback_manager.delete_metadata_with_rollback(file_id)

                # 刪除實體文件
                rollback_manager.delete_file_with_rollback(file_id, storage_path)

                result["files_deleted"] += 1

            except Exception as e:
                error_msg = f"刪除文件 {file_id} 時出錯: {str(e)}"
                result["errors"].append(error_msg)
                logger.error(error_msg, file_id=file_id, task_id=task_id, error=str(e))

        # 刪除任務下的所有資料夾
        try:
            folders = folder_service.list(task_id=task_id)
            for folder in folders:
                folder_id = folder.get("folder_id") or folder.get("_key")
                if folder_id:
                    rollback_manager.delete_folder_with_rollback(folder_id)
                    result["folders_deleted"] += 1
        except Exception as e:
            error_msg = f"刪除任務資料夾時出錯: {str(e)}"
            result["errors"].append(error_msg)
            logger.warning(error_msg, task_id=task_id, error=str(e))

        # 完成事務
        transaction = rollback_manager.complete()
        result["rollback_status"] = transaction.status
        result["total_operations"] = len(transaction.operations)
        result["success_operations"] = transaction.get_success_count()
        result["failed_operations"] = transaction.get_failed_count()

        # 設置最終狀態
        if result["errors"] or result["failed_operations"] > 0:
            if result["files_deleted"] == 0 and not transaction.get_success_count():
                result["status"] = "failed"
            else:
                result["status"] = "partially_completed"
        else:
            result["status"] = "completed"

        result["completed_at"] = datetime.utcnow().isoformat()

        logger.info(
            "Task deletion background job completed",
            task_id=task_id,
            status=result["status"],
            files_deleted=result["files_deleted"],
            folders_deleted=result["folders_deleted"],
        )

        return result

    except Exception as e:
        result["status"] = "failed"
        result["errors"].append(f"Unexpected error: {str(e)}")
        result["completed_at"] = datetime.utcnow().isoformat()
        logger.error(
            "Task deletion background job failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        return result


def execute_permanent_deletion(
    task_id: str,
    user_id: str,
) -> Dict[str, Any]:
    """
    執行任務永久刪除的後台作業

    修改時間：2026-01-21 - 添加永久刪除功能

    直接永久刪除任務，不進行 Soft Delete 標記。
    用於定時清理已過期的 Trash 任務。

    Args:
        task_id: 任務 ID
        user_id: 用戶 ID

    Returns:
        刪除結果字典
    """
    logger.info("Starting task permanent deletion background job", task_id=task_id, user_id=user_id)

    # 調用標準刪除流程，但跳過 Soft Delete 標記
    return execute_task_deletion(
        task_id=task_id,
        user_id=user_id,
        skip_soft_delete=True,
    )


def enqueue_task_deletion(
    task_id: str,
    user_id: str,
) -> str:
    """
    將任務刪除加入 RQ 隊列

    Args:
        task_id: 任務 ID
        user_id: 用戶 ID

    Returns:
        作業 ID (job_id)
    """
    queue = get_task_queue(TASK_DELETION_QUEUE)
    job = queue.enqueue(
        execute_task_deletion,
        task_id=task_id,
        user_id=user_id,
        job_timeout="10m",  # 10 分鐘超時
        result_ttl=3600,  # 結果保存 1 小時
    )
    logger.info(
        "Task deletion job enqueued",
        job_id=job.get_id(),
        task_id=task_id,
        user_id=user_id,
    )
    return job.get_id()
