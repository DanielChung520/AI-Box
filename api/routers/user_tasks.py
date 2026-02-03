# 代碼功能說明: 用戶任務管理路由
# 創建日期: 2025-12-08 09:04:21 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 09:04:21 UTC+8

"""用戶任務管理路由 - 提供任務 CRUD 和同步功能"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Body, Depends, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from api.routers.file_management import get_arangodb_client
from services.api.models.audit_log import AuditAction
from services.api.models.user_task import UserTaskCreate, UserTaskUpdate
from services.api.services.deletion_rollback_manager import DeletionRollbackManager
from services.api.services.file_metadata_service import get_metadata_service
from services.api.services.folder_metadata_service import get_folder_metadata_service
from services.api.services.qdrant_vector_store_service import get_qdrant_vector_store_service
from services.api.services.user_task_service import get_user_task_service
from storage.file_storage import create_storage_from_config
from system.infra.config.config import get_config_section
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/user-tasks", tags=["User Tasks"])


class SyncTasksRequest(BaseModel):
    """同步任務請求模型"""

    tasks: List[Dict[str, Any]] = Field(..., description="任務列表")


@router.get("", name="list_user_tasks")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="task",
    get_resource_id=lambda body: None,
)
async def list_user_tasks(
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    include_archived: bool = Query(False, description="是否包含歸檔的任務"),
    # 修改時間：2026-01-21 - 添加 task_status 參數，支援查詢 Trash 中的任務
    task_status: Optional[str] = Query(None, description="任務狀態過濾（activate/archive/trash）"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """列出當前用戶的所有任務

    修改時間：2026-01-21 - 添加 task_status 參數支援 Trash 查詢

    Args:
        limit: 返回數量限制
        offset: 偏移量
        include_archived: 是否包含歸檔的任務（默認 False，只顯示激活的任務）
        task_status: 任務狀態過濾（activate/archive/trash），為空則返回激活任務
        current_user: 當前認證用戶

    Returns:
        任務列表
    """
    try:
        # 修改時間：2026-01-06 - 隱藏系統管理員的任務，外部用戶看不到
        # 系統管理員的任務只能由系統管理員自己查看
        # 修改時間：2026-01-06 - 優化性能，不構建 fileTree
        service = get_user_task_service()

        # 修改時間：2026-01-21 - 使用 service.list_tasks 進行查詢
        if task_status:
            # 根據指定的 task_status 查詢
            tasks = service.list_tasks(
                user_id=current_user.user_id,
                task_status=task_status,
                limit=limit,
                offset=offset,
            )
        elif current_user.user_id == "systemAdmin":
            # 系統管理員可以查看自己的任務
            tasks = service.list(
                user_id=current_user.user_id,
                limit=limit,
                offset=offset,
                build_file_tree=False,  # 列表查詢不需要 fileTree
            )
        else:
            # 外部用戶不能查看系統管理員的任務
            # 查詢時排除 systemAdmin 的任務
            all_tasks = service.list(
                user_id=current_user.user_id,
                limit=limit * 2,  # 獲取更多任務以補償過濾
                offset=offset,
                build_file_tree=False,  # 列表查詢不需要 fileTree
            )
            # 過濾掉 systemAdmin 的任務（雖然理論上不會出現，但為了安全還是過濾）
            tasks = [
                task
                for task in all_tasks
                if not hasattr(task, "user_id") or task.user_id != "systemAdmin"
            ][
                :limit
            ]  # 限制返回數量

        # 修改時間：2025-12-12 - 添加 include_archived 參數，允許查詢歸檔任務
        # 修改時間：2025-12-09 - 只返回 task_status 為 activate 的任務（或未設置 task_status 的任務，兼容舊數據）
        # 修改時間：2026-01-21 - 如果指定了 task_status，則不進行額外過濾
        if task_status:
            filtered_tasks = tasks
        elif include_archived:
            # 包含所有任務（包括歸檔的）
            filtered_tasks = tasks
        else:
            # 只返回激活的任務
            filtered_tasks = [
                task
                for task in tasks
                if not hasattr(task, "task_status")
                or not task.task_status
                or task.task_status == "activate"
            ]

        return APIResponse.success(
            data={
                "tasks": [
                    task.model_dump(mode="json") if hasattr(task, "model_dump") else task
                    for task in filtered_tasks
                ],
                "total": len(filtered_tasks),
            },
            message="Tasks retrieved successfully",
        )
    except Exception as e:
        logger.error("Failed to list user tasks", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"Failed to list tasks: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{task_id}", name="get_user_task")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="task",
    get_resource_id=lambda body: body.get("task_id"),
)
async def get_user_task(
    task_id: str,
    build_file_tree: bool = Query(False, description="是否構建 fileTree（默認 False，避免超時）"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取指定任務

    修改時間：2026-01-06 - 添加 build_file_tree 參數，默認不構建 fileTree 以提升性能

    Args:
        task_id: 任務 ID
        build_file_tree: 是否構建 fileTree（默認 False，避免超時）
        current_user: 當前認證用戶

    Returns:
        任務數據
    """
    try:
        service = get_user_task_service()

        # 修改時間：2026-01-06 - 添加日誌追蹤和超時保護
        logger.info(
            "get_user_task_start",
            task_id=task_id,
            user_id=current_user.user_id,
            build_file_tree=build_file_tree,
            note="Getting user task - fileTree will be built only if build_file_tree=true",
        )

        import time

        start_time = time.time()
        task = service.get(
            user_id=current_user.user_id,
            task_id=task_id,
            build_file_tree=build_file_tree,  # 傳遞參數
        )
        elapsed_time = time.time() - start_time

        if elapsed_time > 2.0:  # 如果超過2秒，記錄警告
            logger.warning(
                "get_user_task_slow",
                task_id=task_id,
                elapsed_time=elapsed_time,
                build_file_tree=build_file_tree,
                note=f"get_user_task took {elapsed_time:.2f} seconds",
            )

        if task is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(
            "get_user_task_success",
            task_id=task_id,
            elapsed_time=elapsed_time,
            build_file_tree=build_file_tree,
            has_file_tree=bool(task.fileTree),
        )

        return APIResponse.success(
            data=task.model_dump(mode="json"),
            message="Task retrieved successfully",
        )
    except Exception as e:
        logger.error("Failed to get user task", error=str(e), task_id=task_id, exc_info=True)
        return APIResponse.error(
            message=f"Failed to get task: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("", name="create_user_task")
@audit_log(
    action=AuditAction.FILE_CREATE,
    resource_type="task",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def create_user_task(
    request_body: UserTaskCreate = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """創建用戶任務

    Args:
        request_body: 創建任務請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        創建的任務
    """
    import logging
    import time

    std_logger = logging.getLogger("api.routers.user_tasks")
    create_start_time = time.time()

    # 修改時間：2026-01-06 - 在入口處添加詳細日誌
    std_logger.info(
        f"create_user_task START - task_id={request_body.task_id}, user_id={current_user.user_id}, "
        f"title={request_body.title[:50] if request_body.title else 'N/A'}"
    )

    try:
        # 修改時間：2025-01-27 - 使用當前用戶的 user_id，而不是請求體中的 user_id（安全考慮）
        # 確保請求體中的 user_id 與當前用戶匹配（如果提供）
        if request_body.user_id and request_body.user_id != current_user.user_id:
            return APIResponse.error(
                message="User ID mismatch",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 使用當前用戶的 user_id（如果請求體中沒有提供，自動填充）
        if not request_body.user_id:
            request_body.user_id = current_user.user_id

        service = get_user_task_service()
        task = service.create(request_body)

        create_elapsed_time = time.time() - create_start_time
        if create_elapsed_time > 2.0:  # 如果超過2秒，記錄警告
            std_logger.warning(
                f"create_user_task SLOW - task_id={request_body.task_id}, elapsed_time={create_elapsed_time:.2f}s"
            )
            logger.warning(
                "create_user_task_slow",
                task_id=request_body.task_id,
                elapsed_time=create_elapsed_time,
                note=f"create_user_task took {create_elapsed_time:.2f} seconds",
            )

        std_logger.info(
            f"create_user_task SUCCESS - task_id={request_body.task_id}, elapsed_time={create_elapsed_time:.2f}s"
        )
        logger.info(
            "create_user_task_success",
            task_id=request_body.task_id,
            elapsed_time=create_elapsed_time,
        )

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄任務創建操作日誌
        try:
            from services.api.services.operation_log_service import get_operation_log_service

            operation_log_service = get_operation_log_service()

            task_created_at = None
            if hasattr(task, "created_at") and task.created_at:
                if isinstance(task.created_at, datetime):
                    task_created_at = task.created_at.isoformat() + "Z"
                elif isinstance(task.created_at, str):
                    task_created_at = (
                        task.created_at if task.created_at.endswith("Z") else task.created_at + "Z"
                    )

            operation_log_service.log_operation(
                user_id=current_user.user_id,
                resource_id=request_body.task_id,
                resource_type="task",
                resource_name=request_body.title,
                operation_type="create",
                created_at=task_created_at or datetime.utcnow().isoformat() + "Z",
                updated_at=None,
                archived_at=None,
                deleted_at=None,
                notes="任務創建",
            )
        except Exception as e:
            logger.warning("記錄任務創建操作日誌失敗", task_id=request_body.task_id, error=str(e))

        return APIResponse.success(
            data=task.model_dump(mode="json"),
            message="Task created successfully",
        )
    except Exception as e:
        create_elapsed_time = time.time() - create_start_time
        std_logger.error(
            f"create_user_task ERROR after {create_elapsed_time:.2f}s - task_id={request_body.task_id}, error={e}",
            exc_info=True,
        )
        logger.error("Failed to create user task", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"Failed to create task: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{task_id}", name="update_user_task")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="task",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def update_user_task(
    task_id: str,
    request_body: UserTaskUpdate = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """更新用戶任務

    Args:
        task_id: 任務 ID
        request_body: 更新任務請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        更新後的任務
    """
    try:
        service = get_user_task_service()

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 先獲取任務信息，以便記錄操作日誌
        existing_task = service.get(user_id=current_user.user_id, task_id=task_id)
        if existing_task is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        task = service.update(
            user_id=current_user.user_id,
            task_id=task_id,
            update=request_body,
        )

        if task is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄任務更新操作日誌
        try:
            from services.api.services.operation_log_service import get_operation_log_service

            operation_log_service = get_operation_log_service()

            # 處理時間字段
            task_created_at = None
            if hasattr(existing_task, "created_at") and existing_task.created_at:
                if isinstance(existing_task.created_at, datetime):
                    task_created_at = existing_task.created_at.isoformat() + "Z"
                elif isinstance(existing_task.created_at, str):
                    task_created_at = (
                        existing_task.created_at
                        if existing_task.created_at.endswith("Z")
                        else existing_task.created_at + "Z"
                    )

            task_updated_at = datetime.utcnow().isoformat() + "Z"

            # 檢查是否是歸檔操作
            is_archive = False
            if hasattr(request_body, "status") and request_body.status:
                is_archive = request_body.status == "archived"
            if hasattr(request_body, "archived") and request_body.archived:
                is_archive = True

            operation_log_service.log_operation(
                user_id=current_user.user_id,
                resource_id=task_id,
                resource_type="task",
                resource_name=task.title if hasattr(task, "title") else task_id,
                operation_type="archive" if is_archive else "update",
                created_at=task_created_at,
                updated_at=task_updated_at,
                archived_at=task_updated_at if is_archive else None,
                deleted_at=None,
                notes="任務更新" if not is_archive else "任務歸檔",
            )
        except Exception as e:
            logger.warning("記錄任務更新操作日誌失敗", task_id=task_id, error=str(e))

        return APIResponse.success(
            data=task.model_dump(mode="json"),
            message="Task updated successfully",
        )
    except Exception as e:
        logger.error("Failed to update user task", error=str(e), task_id=task_id, exc_info=True)
        return APIResponse.error(
            message=f"Failed to update task: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{task_id}", name="delete_user_task")
@audit_log(
    action=AuditAction.FILE_DELETE,
    resource_type="task",
    get_resource_id=lambda response: None,  # DELETE 請求沒有 body，task_id 從路徑參數獲取
)
async def delete_user_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除用戶任務（多數據源清理）

    刪除任務時需要清理以下數據源：
    1. 任務本身（從 ArangoDB）
    2. 任務下的所有文件（從文件系統）
    3. 所有文件的向量數據（從 Qdrant）
    4. 所有文件的知識圖譜數據（從 ArangoDB）
    5. 所有文件的元數據（從 ArangoDB）

    Args:
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_user_task_service()
        arangodb_client = get_arangodb_client()

        if arangodb_client.db is None:
            return APIResponse.error(
                message="ArangoDB 未連接",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 修改時間：2026-01-21 - 使用靈活的任務查找邏輯
        # 嘗試多種 _key 格式
        collection = arangodb_client.db.collection("user_tasks")
        doc = None

        for doc_key in [f"{current_user.user_id}_{task_id}", task_id]:
            doc = collection.get(doc_key)
            if doc:
                break

        if doc is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 安全檢查：確保任務屬於當前用戶
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != current_user.user_id:
            logger.warning(
                "Attempted to delete task owned by another user",
                task_id=task_id,
                requesting_user=current_user.user_id,
                actual_owner=doc_user_id,
            )
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從文檔構建 UserTask 對象
        task = service.get(user_id=current_user.user_id, task_id=task_id)
        if not task:
            # 如果 service.get 返回 None，但文檔存在且屬於當前用戶，直接使用文檔
            logger.info(
                "Task found directly from ArangoDB",
                task_id=task_id,
                user_id=current_user.user_id,
            )
            # 從文檔構建基本任務信息
            task_title = doc.get("title", task_id)
            task_created_at = doc.get("created_at")
            task_updated_at = doc.get("updated_at")
        else:
            task_title = task.title if hasattr(task, "title") else task_id
            task_created_at = (
                task.created_at if hasattr(task, "created_at") and task.created_at else None
            )
            task_updated_at = (
                task.updated_at if hasattr(task, "updated_at") and task.updated_at else None
            )
        # 處理時間字段（可能是 datetime 對象或字符串）
        task_created_at = None
        if hasattr(task, "created_at") and task.created_at:
            if isinstance(task.created_at, datetime):
                task_created_at = task.created_at
            elif isinstance(task.created_at, str):
                try:
                    task_created_at = datetime.fromisoformat(task.created_at.replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"無法解析 created_at 日期: {e}")
                    task_created_at = None

        task_updated_at = None
        if hasattr(task, "updated_at") and task.updated_at:
            if isinstance(task.updated_at, datetime):
                task_updated_at = task.updated_at
            elif isinstance(task.updated_at, str):
                try:
                    task_updated_at = datetime.fromisoformat(task.updated_at.replace("Z", "+00:00"))
                except (ValueError, TypeError) as e:
                    logger.warning(f"無法解析 updated_at 日期: {e}")
                    task_updated_at = None

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 查找任務下的所有文件
        file_metadata_service = get_metadata_service()
        task_files = file_metadata_service.list(
            user_id=current_user.user_id,
            task_id=task_id,
            limit=1000,
        )

        deletion_results: Dict[str, Any] = {
            "task_deleted": False,
            "files_deleted": 0,
            "folders_deleted": 0,
            "vectors_deleted": 0,
            "kg_deleted": False,
            "errors": [],
        }

        # 使用回滾管理器進行刪除
        vector_store_service = get_qdrant_vector_store_service()
        arangodb_client = get_arangodb_client()
        storage_config = get_config_section("storage")
        storage = create_storage_from_config(storage_config)
        folder_service = get_folder_metadata_service()

        rollback_manager = DeletionRollbackManager(
            task_id=task_id,
            user_id=current_user.user_id,
            vector_store_service=vector_store_service,
            file_metadata_service=file_metadata_service,
            folder_metadata_service=folder_service,
            storage=storage,
            arangodb_client=arangodb_client,
        )

        # 1. 刪除任務下的所有文件
        for file_metadata in task_files:
            file_id = file_metadata.file_id
            storage_path = getattr(file_metadata, "storage_path", None)

            try:
                # 1.1 刪除向量數據（帶重試和回滾追蹤）
                success, error = rollback_manager.delete_vector_with_rollback(file_id, storage_path)
                if success:
                    deletion_results["vectors_deleted"] += 1

                # 1.2 刪除知識圖譜實體
                success, error = rollback_manager.delete_kg_entities_with_rollback(file_id)
                if success:
                    deletion_results["kg_deleted"] = True

                # 1.3 刪除知識圖譜關係
                success, error = rollback_manager.delete_kg_relations_with_rollback(file_id)
                if success and not deletion_results["kg_deleted"]:
                    deletion_results["kg_deleted"] = True

                # 1.4 刪除文件元數據
                success, error = rollback_manager.delete_metadata_with_rollback(file_id)

                # 1.5 刪除實體文件
                success, error = rollback_manager.delete_file_with_rollback(file_id, storage_path)

                deletion_results["files_deleted"] += 1

                # 記錄文件刪除日誌
                try:
                    from services.api.services.operation_log_service import (
                        get_operation_log_service,
                    )

                    operation_log_service = get_operation_log_service()
                    file_created_at = None
                    if hasattr(file_metadata, "created_at") and file_metadata.created_at:
                        if isinstance(file_metadata.created_at, datetime):
                            file_created_at = file_metadata.created_at.isoformat() + "Z"
                        elif isinstance(file_metadata.created_at, str):
                            file_created_at = (
                                file_metadata.created_at
                                if file_metadata.created_at.endswith("Z")
                                else file_metadata.created_at + "Z"
                            )

                    file_updated_at = None
                    if hasattr(file_metadata, "updated_at") and file_metadata.updated_at:
                        if isinstance(file_metadata.updated_at, datetime):
                            file_updated_at = file_metadata.updated_at.isoformat() + "Z"
                        elif isinstance(file_metadata.updated_at, str):
                            file_updated_at = (
                                file_metadata.updated_at
                                if file_metadata.updated_at.endswith("Z")
                                else file_metadata.updated_at + "Z"
                            )

                    operation_log_service.log_operation(
                        user_id=current_user.user_id,
                        resource_id=file_id,
                        resource_type="document",
                        resource_name=(
                            file_metadata.filename
                            if hasattr(file_metadata, "filename")
                            else file_id
                        ),
                        operation_type="delete",
                        created_at=file_created_at,
                        updated_at=file_updated_at,
                        deleted_at=datetime.utcnow().isoformat() + "Z",
                        notes=f"任務刪除時自動刪除，任務ID: {task_id}",
                    )
                except Exception as log_error:
                    logger.warning("記錄文件刪除操作日誌失敗", file_id=file_id, error=str(log_error))

            except Exception as e:
                error_msg = f"刪除文件 {file_id} 時出錯: {str(e)}"
                deletion_results["errors"].append(error_msg)
                logger.error(
                    error_msg, file_id=file_id, task_id=task_id, error=str(e), exc_info=True
                )

        # 2. 刪除任務下的所有資料夾
        try:
            folders = folder_service.list(task_id=task_id)
            for folder in folders:
                folder_id = folder.get("folder_id") or folder.get("_key")
                if folder_id:
                    rollback_manager.delete_folder_with_rollback(folder_id)
                    deletion_results["folders_deleted"] += 1
        except Exception as e:
            error_msg = f"刪除任務資料夾時出錯: {str(e)}"
            deletion_results["errors"].append(error_msg)
            logger.warning(error_msg, task_id=task_id, error=str(e))

        # 3. 刪除任務本身
        success, error = rollback_manager.delete_task_with_rollback(task_id)
        if success:
            deletion_results["task_deleted"] = True

            # 記錄任務刪除日誌
            try:
                from services.api.services.operation_log_service import get_operation_log_service

                operation_log_service = get_operation_log_service()
                task_created_at_str = None
                if task_created_at:
                    if isinstance(task_created_at, datetime):
                        task_created_at_str = task_created_at.isoformat() + "Z"
                    elif isinstance(task_created_at, str):
                        task_created_at_str = (
                            task_created_at
                            if task_created_at.endswith("Z")
                            else task_created_at + "Z"
                        )

                task_updated_at_str = None
                if task_updated_at:
                    if isinstance(task_updated_at, datetime):
                        task_updated_at_str = task_updated_at.isoformat() + "Z"
                    elif isinstance(task_updated_at, str):
                        task_updated_at_str = (
                            task_updated_at
                            if task_updated_at.endswith("Z")
                            else task_updated_at + "Z"
                        )

                operation_log_service.log_operation(
                    user_id=current_user.user_id,
                    resource_id=task_id,
                    resource_type="task",
                    resource_name=task_title,
                    operation_type="delete",
                    created_at=task_created_at_str,
                    updated_at=task_updated_at_str,
                    deleted_at=datetime.utcnow().isoformat() + "Z",
                    notes=f"刪除了 {deletion_results['files_deleted']} 個文件",
                )
            except Exception as e:
                logger.warning("記錄任務刪除操作日誌失敗", task_id=task_id, error=str(e))

        # 完成事務並獲取回滾報告
        transaction = rollback_manager.complete()
        rollback_report = rollback_manager.get_rollback_report()

        # 如果有失敗的操作，添加到 errors
        for op in rollback_report["failed_operations"]:
            error_msg = f"刪除 {op['operation_type']} 失敗 (file_id={op['file_id']}): {op.get('error', 'Unknown error')}"
            if error_msg not in deletion_results["errors"]:
                deletion_results["errors"].append(error_msg)

        # 生成回滾報告摘要
        rollback_summary = {
            "status": transaction.status,
            "total_operations": rollback_report["total_operations"],
            "success_count": rollback_report["success_count"],
            "failed_count": rollback_report["failed_count"],
            "recommendations": rollback_report["recommendations"],
        }

        if not success:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 如果有錯誤，記錄但繼續返回成功（部分刪除成功）
        if deletion_results["errors"]:
            logger.warning(
                "任務刪除完成，但有部分錯誤",
                task_id=task_id,
                errors=deletion_results["errors"],
                deletion_results=deletion_results,
            )

        return APIResponse.success(
            data={
                "deleted": True,
                "deletion_results": deletion_results,
                "rollback_summary": rollback_summary,
            },
            message=f"Task deleted successfully. Deleted {deletion_results['files_deleted']} files and {deletion_results['folders_deleted']} folders.",
        )
    except Exception as e:
        logger.error("Failed to delete user task", error=str(e), task_id=task_id, exc_info=True)
        return APIResponse.error(
            message=f"Failed to delete task: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/sync", name="sync_user_tasks")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="task",
    get_resource_id=lambda body: None,
)
async def sync_user_tasks(
    request_body: SyncTasksRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """同步用戶任務列表（批量創建或更新）

    Args:
        request_body: 同步任務請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        同步結果統計
    """
    try:
        service = get_user_task_service()
        result = service.sync_tasks(
            user_id=current_user.user_id,
            tasks=request_body.tasks,
        )

        return APIResponse.success(
            data=result,
            message=f"Synced {result['total']} tasks (created: {result['created']}, updated: {result['updated']}, errors: {result['errors']})",
        )
    except Exception as e:
        logger.error("Failed to sync user tasks", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"Failed to sync tasks: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/migrate-task", name="migrate_task")
async def migrate_task(
    old_user_id: str = Body(..., embed=True, description="舊的 user_id"),
    new_user_id: str = Body(..., embed=True, description="新的 user_id"),
    task_id: str = Body(..., embed=True, description="任務 ID"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """遷移單個任務到新的 user_id（管理員功能）

    將指定任務從 old_user_id 遷移到 new_user_id。
    注意：由於 _key 包含 user_id，需要重新創建任務文檔。

    Args:
        old_user_id: 舊的 user_id
        new_user_id: 新的 user_id（必須與當前用戶匹配，除非是管理員）
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        遷移結果
    """
    try:
        # 安全檢查：只能遷移到當前用戶的 user_id，除非是系統管理員
        if new_user_id != current_user.user_id and current_user.user_id != "systemAdmin":
            return APIResponse.error(
                message="只能遷移到當前用戶的 user_id，或需要系統管理員權限",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        service = get_user_task_service()
        arangodb_client = get_arangodb_client()

        if arangodb_client.db is None:
            return APIResponse.error(
                message="ArangoDB 未連接",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 獲取舊任務（直接從數據庫讀取，避免動態構建 fileTree）
        collection = arangodb_client.db.collection("user_tasks")
        old_key = f"{old_user_id}_{task_id}"
        new_key = f"{new_user_id}_{task_id}"

        old_task_doc = collection.get(old_key)
        if not old_task_doc:
            return APIResponse.error(
                message=f"任務不存在 (user_id: {old_user_id}, task_id: {task_id})",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從文檔構建 UserTask 對象（用於獲取結構化數據）
        old_task = service.get(user_id=old_user_id, task_id=task_id)
        if not old_task:
            return APIResponse.error(
                message=f"無法讀取任務數據 (user_id: {old_user_id}, task_id: {task_id})",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 使用原始文檔中的 fileTree（如果存在），否則使用動態構建的
        original_filetree = old_task_doc.get("fileTree", old_task.fileTree or [])

        # 檢查新任務是否已存在
        existing = collection.get(new_key)
        if existing:
            # 處理 messages
            messages_data = []
            if old_task.messages:
                for msg in old_task.messages:
                    if hasattr(msg, "model_dump"):
                        messages_data.append(msg.model_dump())
                    elif hasattr(msg, "dict"):
                        messages_data.append(msg.dict())
                    elif isinstance(msg, dict):
                        messages_data.append(msg)
                    else:
                        messages_data.append(str(msg))

            # 處理 executionConfig
            execution_config_data = {}
            if old_task.executionConfig:
                if hasattr(old_task.executionConfig, "model_dump"):
                    execution_config_data = old_task.executionConfig.model_dump()
                elif hasattr(old_task.executionConfig, "dict"):
                    execution_config_data = old_task.executionConfig.dict()
                elif isinstance(old_task.executionConfig, dict):
                    execution_config_data = old_task.executionConfig

            # 處理 fileTree（優先使用原始文檔中的 fileTree）
            filetree_data = []
            filetree_source = original_filetree if original_filetree else (old_task.fileTree or [])
            if filetree_source:
                for node in filetree_source:
                    if hasattr(node, "model_dump"):
                        filetree_data.append(node.model_dump())
                    elif hasattr(node, "dict"):
                        filetree_data.append(node.dict())
                    elif isinstance(node, dict):
                        filetree_data.append(node)

            # 更新現有任務
            collection.update(
                {
                    "_key": new_key,
                    "title": old_task.title,
                    "status": old_task.status,
                    "task_status": old_task.task_status or "activate",
                    "fileTree": filetree_data,
                    "messages": messages_data,
                    "executionConfig": execution_config_data,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            logger.info(
                "任務已存在，已更新",
                old_user_id=old_user_id,
                new_user_id=new_user_id,
                task_id=task_id,
            )
        else:
            # 創建新任務文檔
            # 處理 messages（可能是 Pydantic 模型對象）
            messages_data = []
            if old_task.messages:
                for msg in old_task.messages:
                    if hasattr(msg, "model_dump"):
                        messages_data.append(msg.model_dump())
                    elif hasattr(msg, "dict"):
                        messages_data.append(msg.dict())
                    elif isinstance(msg, dict):
                        messages_data.append(msg)
                    else:
                        messages_data.append(str(msg))

            # 處理 executionConfig
            execution_config_data = {}
            if old_task.executionConfig:
                if hasattr(old_task.executionConfig, "model_dump"):
                    execution_config_data = old_task.executionConfig.model_dump()
                elif hasattr(old_task.executionConfig, "dict"):
                    execution_config_data = old_task.executionConfig.dict()
                elif isinstance(old_task.executionConfig, dict):
                    execution_config_data = old_task.executionConfig

            # 處理 fileTree
            filetree_data = []
            if old_task.fileTree:
                for node in old_task.fileTree:
                    if hasattr(node, "model_dump"):
                        filetree_data.append(node.model_dump())
                    elif hasattr(node, "dict"):
                        filetree_data.append(node.dict())
                    elif isinstance(node, dict):
                        filetree_data.append(node)

            # 處理時間字段
            created_at_str = datetime.utcnow().isoformat()
            if hasattr(old_task, "created_at") and old_task.created_at:
                if isinstance(old_task.created_at, datetime):
                    created_at_str = old_task.created_at.isoformat()
                elif isinstance(old_task.created_at, str):
                    created_at_str = old_task.created_at
                else:
                    created_at_str = str(old_task.created_at)

            new_task_doc = {
                "_key": new_key,
                "task_id": task_id,
                "user_id": new_user_id,
                "title": old_task.title,
                "status": old_task.status,
                "task_status": old_task.task_status or "activate",
                "label_color": old_task.label_color if hasattr(old_task, "label_color") else None,
                "dueDate": old_task.dueDate if hasattr(old_task, "dueDate") else None,
                "messages": messages_data,
                "executionConfig": execution_config_data,
                "fileTree": filetree_data,
                "created_at": created_at_str,
                "updated_at": datetime.utcnow().isoformat(),
            }
            collection.insert(new_task_doc)
            logger.info(
                "任務已遷移",
                old_user_id=old_user_id,
                new_user_id=new_user_id,
                task_id=task_id,
            )

        # 更新文件元數據
        file_collection = arangodb_client.db.collection("file_metadata")

        # 提取所有文件 ID
        def extract_file_ids(node):
            file_ids = []
            if isinstance(node, dict):
                if node.get("type") == "file":
                    file_id = node.get("id")
                    if file_id:
                        file_ids.append(file_id)
                elif node.get("type") == "folder":
                    for child in node.get("children", []):
                        file_ids.extend(extract_file_ids(child))
            elif isinstance(node, list):
                for item in node:
                    file_ids.extend(extract_file_ids(item))
            return file_ids

        # 使用原始 fileTree 提取文件 ID
        file_ids = extract_file_ids(
            original_filetree if original_filetree else (old_task.fileTree or [])
        )
        updated_files = 0

        for file_id in file_ids:
            try:
                file_doc = file_collection.get(file_id)
                if file_doc:
                    file_collection.update(
                        {
                            "_key": file_id,
                            "user_id": new_user_id,
                            "task_id": task_id,
                            "updated_at": datetime.utcnow().isoformat(),
                        }
                    )
                    updated_files += 1
            except Exception as e:
                logger.warning(
                    "更新文件元數據失敗",
                    file_id=file_id,
                    error=str(e),
                )

        # 歸檔舊任務
        try:
            collection.update(
                {
                    "_key": old_key,
                    "task_status": "archive",
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
        except Exception as e:
            logger.warning(
                "歸檔舊任務失敗",
                old_key=old_key,
                error=str(e),
            )

        return APIResponse.success(
            data={
                "migrated": True,
                "task_id": task_id,
                "old_user_id": old_user_id,
                "new_user_id": new_user_id,
                "updated_files": updated_files,
            },
            message=f"任務已成功遷移到 {new_user_id}，更新了 {updated_files} 個文件",
        )
    except Exception as e:
        logger.error("遷移任務失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"遷移失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class FixUserIdRequest(BaseModel):
    """修復用戶 ID 請求"""

    old_user_id: str = Field(..., description="舊的 user_id")
    new_user_id: str = Field(..., description="新的 user_id")
    dry_run: bool = Field(True, description="是否僅預覽，不實際執行")


@router.post("/fix-user-id", name="fix_user_id")
async def fix_user_id(
    request: FixUserIdRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """批量修復任務的 user_id

    將所有屬於 old_user_id 的任務改為 new_user_id。
    這是一個管理員操作，用於修復歷史數據問題。

    Args:
        request: 修復請求
        current_user: 當前認證用戶

    Returns:
        修復結果
    """
    # 只有系統管理員可以執行此操作
    if current_user.user_id != "systemAdmin":
        return APIResponse.error(
            message="只有系統管理員可以執行此操作",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    try:
        arangodb_client = get_arangodb_client()

        if arangodb_client.db is None:
            return APIResponse.error(
                message="ArangoDB 未連接",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        collection = arangodb_client.db.collection("user_tasks")

        # 查找所有屬於 old_user_id 的任務
        aql_query = """
        FOR task IN user_tasks
            FILTER task.user_id == @old_user_id
            RETURN task
        """
        cursor = arangodb_client.db.aql.execute(
            aql_query, bind_vars={"old_user_id": request.old_user_id}
        )
        tasks = list(cursor)

        total_tasks = len(tasks)
        logger.info(
            "fix_user_id_start",
            old_user_id=request.old_user_id,
            new_user_id=request.new_user_id,
            total_tasks=total_tasks,
            dry_run=request.dry_run,
        )

        if total_tasks == 0:
            return APIResponse.success(
                data={
                    "dry_run": request.dry_run,
                    "total_tasks": 0,
                    "fixed_tasks": 0,
                    "skipped_tasks": 0,
                },
                message=f"沒有找到屬於 {request.old_user_id} 的任務",
            )

        # 預覽模式
        if request.dry_run:
            # 顯示前 10 個任務
            sample_tasks = [
                {
                    "task_id": task.get("task_id"),
                    "title": task.get("title", "")[:30],
                }
                for task in tasks[:10]
            ]
            return APIResponse.success(
                data={
                    "dry_run": True,
                    "total_tasks": total_tasks,
                    "fixed_tasks": 0,
                    "skipped_tasks": 0,
                    "sample_tasks": sample_tasks,
                },
                message=f"預覽：找到 {total_tasks} 個任務，添加 --apply 參數來實際執行修復",
            )

        # 執行修復
        fixed_count = 0
        skipped_count = 0
        for task in tasks:
            task_id = task.get("task_id")
            old_key = f"{request.old_user_id}_{task_id}"
            new_key = f"{request.new_user_id}_{task_id}"

            # 檢查目標是否已存在
            existing = collection.get(new_key)
            if existing:
                skipped_count += 1
                logger.info(
                    "任務已存在，跳過",
                    task_id=task_id,
                    new_user_id=request.new_user_id,
                )
                continue

            try:
                # 更新 user_id
                collection.update_match({"_key": old_key}, {"user_id": request.new_user_id})
                fixed_count += 1
                logger.info(
                    "已修復任務",
                    task_id=task_id,
                    old_user_id=request.old_user_id,
                    new_user_id=request.new_user_id,
                )
            except Exception as e:
                logger.error(
                    "修復任務失敗",
                    task_id=task_id,
                    error=str(e),
                )

        return APIResponse.success(
            data={
                "dry_run": False,
                "total_tasks": total_tasks,
                "fixed_tasks": fixed_count,
                "skipped_tasks": skipped_count,
            },
            message=f"修復完成：{fixed_count} 個任務已修復，{skipped_count} 個任務已存在",
        )

    except Exception as e:
        logger.error("修復用戶 ID 失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"修復失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{task_id}/async", name="delete_user_task_async")
@audit_log(
    action=AuditAction.FILE_DELETE,
    resource_type="task",
    get_resource_id=lambda response: None,
)
async def delete_user_task_async(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """異步刪除用戶任務（多數據源清理）

    將任務刪除加入 RQ 隊列異步執行，立即返回 job_id。
    前端可通過 /api/v1/user-tasks/jobs/{job_id} 查詢進度。

    Args:
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        包含 job_id 的刪除任務信息
    """
    try:
        from services.api.tasks.task_deletion import enqueue_task_deletion

        arangodb_client = get_arangodb_client()

        if arangodb_client.db is None:
            return APIResponse.error(
                message="ArangoDB 未連接",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 檢查任務是否存在且屬於當前用戶
        collection = arangodb_client.db.collection("user_tasks")
        doc = None

        for doc_key in [f"{current_user.user_id}_{task_id}", task_id]:
            doc = collection.get(doc_key)
            if doc:
                break

        if doc is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 確保任務屬於當前用戶
        doc_user_id = doc.get("user_id")
        if doc_user_id and doc_user_id != current_user.user_id:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 將刪除任務加入 RQ 隊列
        job_id = enqueue_task_deletion(
            task_id=task_id,
            user_id=current_user.user_id,
        )

        logger.info(
            "Task deletion job enqueued",
            task_id=task_id,
            user_id=current_user.user_id,
            job_id=job_id,
        )

        return APIResponse.success(
            data={
                "job_id": job_id,
                "task_id": task_id,
                "status": "queued",
                "message": "任務刪除已加入隊列，請通過 /api/v1/user-tasks/jobs/{job_id} 查詢進度",
            },
            message="任務刪除已提交",
        )

    except Exception as e:
        logger.error(
            "Failed to enqueue task deletion", error=str(e), task_id=task_id, exc_info=True
        )
        return APIResponse.error(
            message=f"提交刪除任務失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/jobs/{job_id}", name="get_job_status")
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查詢異步任務狀態

    Args:
        job_id: 任務 ID（RQ job_id）
        current_user: 當前認證用戶

    Returns:
        任務狀態信息
    """
    try:
        from database.rq.queue import TASK_DELETION_QUEUE, get_task_queue

        queue = get_task_queue(TASK_DELETION_QUEUE)
        job = queue.fetch_job(job_id)

        if job is None:
            return APIResponse.error(
                message="Job not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 獲取任務結果
        result = job.get_result()
        job_status = job.get_status()

        response_data = {
            "job_id": job_id,
            "status": job_status,
            "started_at": job.enqueued_at.isoformat() if job.enqueued_at else None,
            "ended_at": job.ended_at.isoformat() if job.ended_at else None,
        }

        # 根據狀態返回不同信息
        if job_status == "finished":
            response_data["data"] = result
            if result and result.get("status") == "completed":
                response_data[
                    "message"
                ] = f"任務刪除完成。已刪除 {result.get('files_deleted', 0)} 個文件，{result.get('folders_deleted', 0)} 個資料夾。"
            elif result and result.get("status") == "partially_completed":
                response_data[
                    "message"
                ] = f"任務部分刪除完成。刪除了 {result.get('files_deleted', 0)} 個文件，{result.get('folders_deleted', 0)} 個資料夾。"
            else:
                response_data["message"] = "任務刪除完成"
        elif job_status == "failed":
            response_data["message"] = "任務刪除失敗"
            if result:
                response_data["errors"] = result.get("errors", [])
        elif job_status in ["started", "queued"]:
            response_data["message"] = "任務正在處理中..."
        else:
            response_data["message"] = f"任務狀態: {job_status}"

        return APIResponse.success(data=response_data, message=response_data["message"])

    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"查詢任務狀態失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/{task_id}/soft-delete", name="soft_delete_task")
@audit_log(
    action=AuditAction.TASK_DELETE,
    resource_type="task",
    get_resource_id=lambda response: None,
)
async def soft_delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """軟刪除用戶任務（移至 Trash）

    修改時間：2026-01-21 - 添加 Soft Delete 機制

    將任務的 task_status 改為 "trash"，並設置 deleted_at 和 permanent_delete_at。
    任務將在 7 天後自動永久刪除，或用戶可以提前恢復或永久刪除。

    Args:
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        軟刪除結果
    """
    try:
        service = get_user_task_service()

        result = service.soft_delete(
            user_id=current_user.user_id,
            task_id=task_id,
        )

        if not result.get("success"):
            return APIResponse.error(
                message=result.get("error", "Soft delete failed"),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(
            "Task soft-deleted",
            task_id=task_id,
            user_id=current_user.user_id,
            deleted_at=result.get("deleted_at"),
            permanent_delete_at=result.get("permanent_delete_at"),
        )

        return APIResponse.success(
            data=result,
            message="任務已移至 Trash，將在 7 天後永久刪除",
        )

    except Exception as e:
        logger.error(
            "Failed to soft delete task",
            task_id=task_id,
            user_id=current_user.user_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"軟刪除任務失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/{task_id}/restore", name="restore_task")
@audit_log(
    action=AuditAction.TASK_UPDATE,
    resource_type="task",
    get_resource_id=lambda response: None,
)
async def restore_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """恢復用戶任務（從 Trash 恢復）

    修改時間：2026-01-21 - 添加恢復功能

    將 Trash 中的任務恢復到正常狀態（task_status = "activate"），
    並清除 deleted_at 和 permanent_delete_at。

    Args:
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        恢復結果
    """
    try:
        service = get_user_task_service()

        result = service.restore(
            user_id=current_user.user_id,
            task_id=task_id,
        )

        if not result.get("success"):
            return APIResponse.error(
                message=result.get("error", "Restore failed"),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Task restored from trash",
            task_id=task_id,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data=result,
            message="任務已恢復",
        )

    except Exception as e:
        logger.error(
            "Failed to restore task",
            task_id=task_id,
            user_id=current_user.user_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"恢復任務失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{task_id}/permanent", name="permanent_delete_task")
@audit_log(
    action=AuditAction.TASK_DELETE,
    resource_type="task",
    get_resource_id=lambda response: None,
)
async def permanent_delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """永久刪除用戶任務（從 Trash 徹底刪除）

    修改時間：2026-01-21 - 添加永久刪除功能

    從 Trash 中徹底刪除任務（不可恢復）。

    Args:
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_user_task_service()

        result = service.permanent_delete(
            user_id=current_user.user_id,
            task_id=task_id,
        )

        if not result.get("success"):
            return APIResponse.error(
                message=result.get("error", "Permanent delete failed"),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Task permanently deleted",
            task_id=task_id,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data=result,
            message="任務已永久刪除",
        )

    except Exception as e:
        logger.error(
            "Failed to permanently delete task",
            task_id=task_id,
            user_id=current_user.user_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"永久刪除任務失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
