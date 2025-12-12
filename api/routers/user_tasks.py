# 代碼功能說明: 用戶任務管理路由
# 創建日期: 2025-12-08 09:04:21 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 09:04:21 UTC+8

"""用戶任務管理路由 - 提供任務 CRUD 和同步功能"""

from typing import List, Dict, Any
from fastapi import APIRouter, Query, status, Depends, Body
from fastapi.responses import JSONResponse
import structlog
from datetime import datetime

from api.core.response import APIResponse
from services.api.services.user_task_service import get_user_task_service
from services.api.models.user_task import (
    UserTaskCreate,
    UserTaskUpdate,
)
from system.security.dependencies import get_current_user
from system.security.models import User
from system.security.audit_decorator import audit_log
from services.api.models.audit_log import AuditAction
from fastapi import Request
from pydantic import BaseModel, Field
from services.api.services.file_metadata_service import (
    get_metadata_service,
)
from services.api.services.vector_store_service import get_vector_store_service
from storage.file_storage import create_storage_from_config
from system.infra.config.config import get_config_section
from api.routers.file_management import get_arangodb_client

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
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """列出當前用戶的所有任務

    Args:
        limit: 返回數量限制
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        任務列表
    """
    try:
        service = get_user_task_service()
        tasks = service.list(
            user_id=current_user.user_id,
            limit=limit,
            offset=offset,
        )

        # 修改時間：2025-12-09 - 只返回 task_status 為 activate 的任務（或未設置 task_status 的任務，兼容舊數據）
        filtered_tasks = [
            task
            for task in tasks
            if not hasattr(task, "task_status")
            or not task.task_status
            or task.task_status == "activate"
        ]

        return APIResponse.success(
            data={
                "tasks": [task.model_dump(mode="json") for task in filtered_tasks],
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
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取指定任務

    Args:
        task_id: 任務 ID
        current_user: 當前認證用戶

    Returns:
        任務數據
    """
    try:
        service = get_user_task_service()
        task = service.get(user_id=current_user.user_id, task_id=task_id)

        if task is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(
            data=task.model_dump(mode="json"),
            message="Task retrieved successfully",
        )
    except Exception as e:
        logger.error(
            "Failed to get user task", error=str(e), task_id=task_id, exc_info=True
        )
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
    request: Request = None,
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

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄任務創建操作日誌
        try:
            from services.api.services.operation_log_service import (
                get_operation_log_service,
            )

            operation_log_service = get_operation_log_service()

            task_created_at = None
            if hasattr(task, "created_at") and task.created_at:
                if isinstance(task.created_at, datetime):
                    task_created_at = task.created_at.isoformat() + "Z"
                elif isinstance(task.created_at, str):
                    task_created_at = (
                        task.created_at
                        if task.created_at.endswith("Z")
                        else task.created_at + "Z"
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
            logger.warning(
                "記錄任務創建操作日誌失敗", task_id=request_body.task_id, error=str(e)
            )

        return APIResponse.success(
            data=task.model_dump(mode="json"),
            message="Task created successfully",
        )
    except Exception as e:
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
    request: Request = None,
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
            from services.api.services.operation_log_service import (
                get_operation_log_service,
            )

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
        logger.error(
            "Failed to update user task", error=str(e), task_id=task_id, exc_info=True
        )
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
    3. 所有文件的向量數據（從 ChromaDB）
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

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 先獲取任務信息，以便記錄操作日誌
        task = service.get(user_id=current_user.user_id, task_id=task_id)
        if not task:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        task_title = task.title if hasattr(task, "title") else task_id
        # 處理時間字段（可能是 datetime 對象或字符串）
        task_created_at = None
        if hasattr(task, "created_at") and task.created_at:
            if isinstance(task.created_at, datetime):
                task_created_at = task.created_at
            elif isinstance(task.created_at, str):
                try:
                    task_created_at = datetime.fromisoformat(
                        task.created_at.replace("Z", "+00:00")
                    )
                except:
                    task_created_at = None

        task_updated_at = None
        if hasattr(task, "updated_at") and task.updated_at:
            if isinstance(task.updated_at, datetime):
                task_updated_at = task.updated_at
            elif isinstance(task.updated_at, str):
                try:
                    task_updated_at = datetime.fromisoformat(
                        task.updated_at.replace("Z", "+00:00")
                    )
                except:
                    task_updated_at = None

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 查找任務下的所有文件
        file_metadata_service = get_metadata_service()
        task_files = file_metadata_service.list(
            user_id=current_user.user_id,
            task_id=task_id,
            limit=1000,
        )

        deletion_results = {
            "task_deleted": False,
            "files_deleted": 0,
            "folders_deleted": 0,  # 修改時間：2025-12-09 - 添加資料夾刪除計數
            "vectors_deleted": 0,
            "kg_deleted": False,
            "errors": [],
        }

        # 1. 刪除任務下的所有文件（包括向量、圖譜、元數據、實體文件）
        vector_store_service = get_vector_store_service()
        arangodb_client = get_arangodb_client()
        storage_config = get_config_section("storage")
        storage = create_storage_from_config(storage_config)

        for file_metadata in task_files:
            file_id = file_metadata.file_id
            try:
                # 1.1 刪除 ChromaDB 中的向量數據
                try:
                    vector_store_service.delete_vectors_by_file_id(
                        file_id=file_id, user_id=current_user.user_id
                    )
                    deletion_results["vectors_deleted"] += 1
                    logger.info("向量數據刪除成功", file_id=file_id, task_id=task_id)
                except Exception as e:
                    error_msg = f"刪除向量數據失敗: {str(e)}"
                    deletion_results["errors"].append(error_msg)
                    logger.warning(
                        error_msg, file_id=file_id, task_id=task_id, error=str(e)
                    )

                # 1.2 刪除知識圖譜關聯（從 ArangoDB 中刪除與該文件相關的實體和關係）
                if (
                    arangodb_client.db is not None
                    and arangodb_client.db.aql is not None
                ):
                    entities_collection = "entities"
                    relations_collection = "relations"

                    if arangodb_client.db.has_collection(entities_collection):
                        try:
                            aql_query_entities = """
                            FOR entity IN entities
                                FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                                REMOVE entity IN entities
                            """
                            arangodb_client.db.aql.execute(
                                aql_query_entities, bind_vars={"file_id": file_id}
                            )
                        except Exception as e:
                            logger.warning(
                                "刪除實體時出錯", file_id=file_id, error=str(e)
                            )

                    if arangodb_client.db.has_collection(relations_collection):
                        try:
                            aql_query_relations = """
                            FOR relation IN relations
                                FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                                REMOVE relation IN relations
                            """
                            arangodb_client.db.aql.execute(
                                aql_query_relations, bind_vars={"file_id": file_id}
                            )
                        except Exception as e:
                            logger.warning(
                                "刪除關係時出錯", file_id=file_id, error=str(e)
                            )

                    deletion_results["kg_deleted"] = True
                    logger.info(
                        "知識圖譜關聯刪除成功", file_id=file_id, task_id=task_id
                    )

                # 1.3 刪除文件元數據（從 ArangoDB）
                try:
                    file_metadata_service.delete(file_id)
                    logger.info("文件元數據刪除成功", file_id=file_id, task_id=task_id)
                except Exception as e:
                    error_msg = f"刪除文件元數據失敗: {str(e)}"
                    deletion_results["errors"].append(error_msg)
                    logger.warning(
                        error_msg, file_id=file_id, task_id=task_id, error=str(e)
                    )

                # 1.4 刪除實體文件（從文件系統）
                try:
                    storage.delete_file(file_id)
                    logger.info("實體文件刪除成功", file_id=file_id, task_id=task_id)
                except Exception as e:
                    error_msg = f"刪除實體文件失敗: {str(e)}"
                    deletion_results["errors"].append(error_msg)
                    logger.warning(
                        error_msg, file_id=file_id, task_id=task_id, error=str(e)
                    )

                deletion_results["files_deleted"] += 1

                # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄文件刪除操作日誌
                try:
                    from services.api.services.operation_log_service import (
                        get_operation_log_service,
                    )

                    operation_log_service = get_operation_log_service()
                    # 處理文件時間字段
                    file_created_at = None
                    if (
                        hasattr(file_metadata, "created_at")
                        and file_metadata.created_at
                    ):
                        if isinstance(file_metadata.created_at, datetime):
                            file_created_at = file_metadata.created_at.isoformat() + "Z"
                        elif isinstance(file_metadata.created_at, str):
                            file_created_at = (
                                file_metadata.created_at
                                if file_metadata.created_at.endswith("Z")
                                else file_metadata.created_at + "Z"
                            )

                    file_updated_at = None
                    if (
                        hasattr(file_metadata, "updated_at")
                        and file_metadata.updated_at
                    ):
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
                except Exception as e:
                    logger.warning(
                        "記錄文件刪除操作日誌失敗", file_id=file_id, error=str(e)
                    )

            except Exception as e:
                error_msg = f"刪除文件 {file_id} 時出錯: {str(e)}"
                deletion_results["errors"].append(error_msg)
                logger.error(
                    error_msg,
                    file_id=file_id,
                    task_id=task_id,
                    error=str(e),
                    exc_info=True,
                )

        # 修改時間：2025-12-09 - 刪除任務下的所有資料夾
        if arangodb_client.db is not None:
            try:
                from api.routers.file_management import FOLDER_COLLECTION_NAME

                folder_collection = arangodb_client.db.collection(
                    FOLDER_COLLECTION_NAME
                )

                # 查詢任務下的所有資料夾
                aql_query = """
                FOR folder IN folder_metadata
                    FILTER folder.task_id == @task_id
                    RETURN folder._key
                """
                cursor = arangodb_client.db.aql.execute(
                    aql_query,
                    bind_vars={"task_id": task_id},
                )
                folder_ids = list(cursor)

                # 刪除所有資料夾
                for folder_id in folder_ids:
                    try:
                        folder_collection.delete(folder_id)
                        deletion_results["folders_deleted"] += 1
                        logger.info(
                            "資料夾刪除成功", folder_id=folder_id, task_id=task_id
                        )
                    except Exception as e:
                        error_msg = f"刪除資料夾 {folder_id} 失敗: {str(e)}"
                        deletion_results["errors"].append(error_msg)
                        logger.warning(
                            error_msg,
                            folder_id=folder_id,
                            task_id=task_id,
                            error=str(e),
                        )

                logger.info(
                    "任務資料夾刪除完成",
                    task_id=task_id,
                    folders_deleted=deletion_results["folders_deleted"],
                )
            except Exception as e:
                error_msg = f"刪除任務資料夾時出錯: {str(e)}"
                deletion_results["errors"].append(error_msg)
                logger.warning(error_msg, task_id=task_id, error=str(e))

        # 2. 刪除任務本身（從 ArangoDB）
        success = service.delete(user_id=current_user.user_id, task_id=task_id)
        if success:
            deletion_results["task_deleted"] = True

            # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄任務刪除操作日誌
            try:
                from services.api.services.operation_log_service import (
                    get_operation_log_service,
                )

                operation_log_service = get_operation_log_service()
                # 處理任務時間字段
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
                logger.warning(
                    "記錄任務刪除操作日誌失敗", task_id=task_id, error=str(e)
                )

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
            },
            message=f"Task deleted successfully. Deleted {deletion_results['files_deleted']} files and {deletion_results['folders_deleted']} folders.",
        )
    except Exception as e:
        logger.error(
            "Failed to delete user task", error=str(e), task_id=task_id, exc_info=True
        )
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
    request: Request = None,
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
