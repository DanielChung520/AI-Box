# 代碼功能說明: 文件管理路由
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-09

"""文件管理路由 - 提供文件列表查詢、搜索、下載、預覽等功能"""

import io
import os
import zipfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import structlog
from fastapi import APIRouter, Body, Depends, Query, Request, status

# 延遲導入 botocore，避免在未安裝時導致模塊級導入錯誤
try:
    from botocore.exceptions import ConnectionClosedError
except ImportError:
    # 如果 botocore 未安裝，定義一個占位符類
    ConnectionClosedError = Exception  # type: ignore[misc,assignment]
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from database.arangodb import ArangoDBClient
from database.rq.queue import KG_EXTRACTION_QUEUE, VECTORIZATION_QUEUE, get_task_queue
from services.api.models.audit_log import AuditAction
from services.api.models.file_metadata import FileMetadata
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.file_permission_service import get_file_permission_service
from services.api.services.file_tree_sync_service import get_file_tree_sync_service
from services.api.services.vector_store_service import get_vector_store_service
from services.api.utils.file_validator import FileValidator, create_validator_from_config
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import Permission, User
from workers.tasks import process_kg_extraction_only_task, process_vectorization_only_task

# 导入 worker 配置函数
try:
    from services.api.services.config_store_service import ConfigStoreService

    _worker_config_service: Optional[ConfigStoreService] = None

    def get_worker_config_service() -> ConfigStoreService:
        """獲取配置存儲服務實例（單例模式）"""
        global _worker_config_service
        if _worker_config_service is None:
            _worker_config_service = ConfigStoreService()
        return _worker_config_service

    WORKER_CONFIG_STORE_AVAILABLE = True
except ImportError:
    WORKER_CONFIG_STORE_AVAILABLE = False


def get_worker_job_timeout() -> int:
    """獲取 RQ Worker 任務超時時間（秒），優先從 ArangoDB system_configs 讀取"""
    # 優先從 ArangoDB system_configs 讀取
    if WORKER_CONFIG_STORE_AVAILABLE:
        try:
            config_service = get_worker_config_service()
            config = config_service.get_config("worker", tenant_id=None)
            if config and config.config_data:
                timeout = config.config_data.get("job_timeout", 3600)
                logger.debug(f"使用 ArangoDB system_configs 中的 worker.job_timeout: {timeout}")
                return int(timeout)
        except Exception as e:
            logger.warning(
                "failed_to_load_worker_config_from_arangodb",
                error=str(e),
                message="從 ArangoDB 讀取 worker 配置失敗，使用默認值 900 秒",
            )

    # 默認值：900 秒（15分鐘）- 測試階段快速發現問題；生產環境可調整為 3600 秒
    return 900


logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["File Management"])

# 全局服務實例（懶加載）
_metadata_service: Optional[FileMetadataService] = None
_storage: Optional[FileStorage] = None
_arangodb_client: Optional[ArangoDBClient] = None
_validator: Optional[FileValidator] = None


# 請求模型
class FileRenameRequest(BaseModel):
    """文件重命名請求模型"""

    new_name: str = Field(..., description="新文件名", min_length=1, max_length=255)


class FileCopyRequest(BaseModel):
    """文件複製請求模型"""

    target_task_id: Optional[str] = Field(None, description="目標任務ID（可選）")


class FileMoveRequest(BaseModel):
    """文件移動請求模型"""

    target_task_id: str = Field(..., description="目標任務ID")
    target_folder_id: Optional[str] = Field(None, description="目標資料夾ID（可選，未提供時移動到任務工作區）")


class FolderCreateRequest(BaseModel):
    """創建資料夾請求模型"""

    folder_name: str = Field(..., description="資料夾名稱", min_length=1, max_length=255)
    parent_task_id: Optional[str] = Field(None, description="父任務ID（可選）")


class FolderRenameRequest(BaseModel):
    """重命名資料夾請求模型"""

    new_name: str = Field(..., description="新資料夾名稱", min_length=1, max_length=255)


class FolderMoveRequest(BaseModel):
    """移動資料夾請求模型"""

    parent_task_id: Optional[str] = Field(None, description="目標父任務ID（None 表示移動到根節點）")


class BatchDownloadRequest(BaseModel):
    """批量下載請求模型"""

    file_ids: List[str] = Field(..., description="文件ID列表", min_items=1)


class LibraryUploadRequest(BaseModel):
    """從文件庫上傳請求模型"""

    file_ids: List[str] = Field(..., description="文件ID列表", min_items=1)
    target_task_id: str = Field(..., description="目標任務ID")


class LibraryReturnRequest(BaseModel):
    """傳回文件庫請求模型"""

    file_ids: List[str] = Field(..., description="文件ID列表", min_items=1)


class SyncFilesRequest(BaseModel):
    """同步文件請求模型"""

    task_id: Optional[str] = Field(None, description="任務ID（可選）")
    file_ids: Optional[List[str]] = Field(None, description="文件ID列表（可選）")


def get_arangodb_client() -> ArangoDBClient:
    """獲取ArangoDB客戶端實例（單例模式）"""
    global _arangodb_client
    if _arangodb_client is None:
        _arangodb_client = ArangoDBClient()
    return _arangodb_client


def get_metadata_service() -> FileMetadataService:
    """獲取元數據服務實例（單例模式）"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service


def get_storage() -> FileStorage:
    """獲取文件存儲實例（單例模式）"""
    global _storage
    if _storage is None:
        config = get_config_section("file_upload", default={}) or {}
        _storage = create_storage_from_config(config)
    return _storage


def get_validator() -> FileValidator:
    """獲取文件驗證器實例（單例模式）"""
    global _validator
    if _validator is None:
        config = get_config_section("file_upload", default={}) or {}
        _validator = create_validator_from_config(config)
    return _validator


@router.get("")
async def list_files(
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    task_id: Optional[str] = Query(None, description="任務 ID"),
    file_type: Optional[str] = Query(None, description="文件類型篩選"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    sort_by: str = Query("upload_time", description="排序字段"),
    sort_order: str = Query("desc", description="排序順序（asc/desc）"),
    current_user: User = Depends(get_current_user),
    view_all_files: bool = Query(
        False, description="是否查看所有文件（僅限管理員）"
    ),  # 修改時間：2026-01-06 - 添加 view_all_files 參數
) -> JSONResponse:
    """獲取文件列表

    Args:
        user_id: 用戶ID（如果未提供，使用當前用戶ID）
        task_id: 任務ID（可選）
        file_type: 文件類型篩選
        limit: 返回數量限制
        offset: 偏移量
        sort_by: 排序字段
        sort_order: 排序順序
        current_user: 當前認證用戶
        view_all_files: 是否查看所有文件（僅限管理員）

    Returns:
        文件列表
    """
    try:
        # 修改時間：2026-01-06 - 支持管理員查看所有文件
        # 檢查是否為管理員且明確請求查看所有文件
        is_admin = current_user.has_permission(Permission.ALL.value)
        # 如果明確傳遞了 view_all_files=True，且用戶是管理員，則查看所有文件
        # 否則，如果未提供 user_id 和 task_id，且用戶是管理員，也視為查看所有文件（向後兼容）
        view_all_files_flag = (
            view_all_files and is_admin or (is_admin and user_id is None and task_id is None)
        )

        if view_all_files_flag:
            # 管理員查看所有文件，不設置 user_id 和 task_id
            user_id = None
            task_id = None
        else:
            # 如果未提供user_id，使用當前用戶ID
            if user_id is None:
                user_id = current_user.user_id

            # 如果查詢其他用戶的文件，檢查權限
            if user_id != current_user.user_id:
                get_file_permission_service()
                if not current_user.has_permission(Permission.ALL.value):
                    # 非管理員只能查看自己的文件
                    user_id = current_user.user_id

            # 修改時間：2025-12-09 - 如果提供了 task_id，檢查任務是否屬於當前用戶
            if task_id:
                permission_service = get_file_permission_service()
                if not permission_service.check_task_file_access(
                    user=current_user,
                    task_id=task_id,
                    required_permission=Permission.FILE_READ.value,
                ):
                    return APIResponse.error(
                        message=f"任務 {task_id} 不存在或不屬於當前用戶",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        service = get_metadata_service()
        # 修改時間：2026-01-06 - 如果管理員要查看所有文件，使用特殊的查詢方法
        if view_all_files_flag:
            # 直接查詢所有文件（不限制 user_id 和 task_id）
            if service.client.db is None:
                raise RuntimeError("ArangoDB client is not connected")
            if service.client.db.aql is None:
                raise RuntimeError("ArangoDB AQL is not available")

            filter_conditions = []
            bind_vars: dict = {}

            if file_type:
                filter_conditions.append("doc.file_type == @file_type")
                bind_vars["file_type"] = file_type

            # 優化 AQL 查詢：直接返回需要的字段，減少數據傳輸
            aql = "FOR doc IN file_metadata"
            if filter_conditions:
                aql += " FILTER " + " AND ".join(filter_conditions)

            # 使用索引字段排序（upload_time 有索引）
            sort_field = (
                sort_by if sort_by in ["upload_time", "created_at", "updated_at"] else "upload_time"
            )
            aql += f" SORT doc.{sort_field} {sort_order.upper()}"

            if offset > 0:
                aql += " LIMIT @offset, @limit"
                bind_vars["offset"] = offset
                bind_vars["limit"] = limit
            else:
                aql += " LIMIT @limit"
                bind_vars["limit"] = limit

            aql += " RETURN doc"

            cursor = service.client.db.aql.execute(aql, bind_vars=bind_vars)
            results = [FileMetadata(**doc) for doc in cursor]
        else:
            results = service.list(
                file_type=file_type,
                user_id=user_id,
                task_id=task_id,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            )

        return APIResponse.success(
            data={
                "files": [m.model_dump(mode="json") for m in results],
                "total": len(results),
                "limit": limit,
                "offset": offset,
            },
            message="文件列表查詢成功",
        )
    except Exception as e:
        logger.error("Failed to list files", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"查詢文件列表失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/search")
async def search_files(
    query: str = Query(..., description="搜索關鍵字"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    file_type: Optional[str] = Query(None, description="文件類型篩選"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """搜索文件

    Args:
        query: 搜索關鍵字
        user_id: 用戶ID（如果未提供，使用當前用戶ID）
        file_type: 文件類型篩選
        limit: 返回數量限制
        current_user: 當前認證用戶

    Returns:
        搜索結果
    """
    try:
        # 如果未提供user_id，使用當前用戶ID
        if user_id is None:
            user_id = current_user.user_id

        # 如果查詢其他用戶的文件，檢查權限
        if user_id != current_user.user_id:
            get_file_permission_service()
            if not current_user.has_permission(Permission.ALL.value):
                # 非管理員只能搜索自己的文件
                user_id = current_user.user_id

        service = get_metadata_service()
        results = service.search(query=query, user_id=user_id, file_type=file_type, limit=limit)

        return APIResponse.success(
            data={
                "files": [m.model_dump(mode="json") for m in results],
                "total": len(results),
                "query": query,
            },
            message="文件搜索成功",
        )
    except Exception as e:
        logger.error("Failed to search files", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"搜索文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/tree", name="get_file_tree")
async def get_file_tree(
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    task_id: Optional[str] = Query(None, description="任務 ID"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取文件樹結構（按任務ID組織）

    Args:
        user_id: 用戶ID（如果未提供，使用當前用戶ID）
        task_id: 任務ID（可選，如果提供則只返回該任務的文件）
        current_user: 當前認證用戶

    Returns:
        文件樹結構
    """
    try:
        # 優先使用當前認證用戶的 user_id，確保查詢到正確的文件
        # 如果前端傳遞的 user_id 與當前用戶不匹配，使用當前用戶的 user_id
        effective_user_id = current_user.user_id
        if user_id and user_id != current_user.user_id:
            # 如果傳遞的 user_id 與當前用戶不匹配，記錄警告但使用當前用戶的 user_id
            logger.warning(
                "User ID mismatch in file tree query",
                requested_user_id=user_id,
                current_user_id=current_user.user_id,
            )

        service = get_metadata_service()

        # 修改時間：2025-01-27 - 移除 temp-workspace，task_id 必須提供
        # 每個任務都有獨立的任務工作區，文件查詢必須指定 task_id
        if not task_id:
            # 如果未指定 task_id，返回錯誤（不再支持查詢所有文件）
            return APIResponse.error(
                message="必須提供 task_id 參數，文件必須關聯到任務工作區",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 修改時間：2025-12-09 - 檢查任務是否屬於當前用戶
        permission_service = get_file_permission_service()
        if not permission_service.check_task_file_access(
            user=current_user,
            task_id=task_id,
            required_permission=Permission.FILE_READ.value,
        ):
            return APIResponse.error(
                message=f"任務 {task_id} 不存在或不屬於當前用戶",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 只查詢指定 task_id 的文件（該任務的任務工作區）
        try:
            all_files = service.list(
                user_id=effective_user_id,
                task_id=task_id,
                limit=1000,
            )
        except Exception as list_error:
            logger.error(
                "Failed to list files",
                error=str(list_error),
                task_id=task_id,
                user_id=effective_user_id,
                exc_info=True,
            )
            # 如果查詢文件失敗，返回空列表而不是拋出異常
            all_files = []

        # 獲取所有資料夾（如果指定了task_id則過濾父資料夾）
        # 確保資料夾集合存在
        try:
            _ensure_folder_collection()
        except Exception as folder_collection_error:
            logger.error(
                "Failed to ensure folder collection",
                error=str(folder_collection_error),
                task_id=task_id,
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to ensure folder collection: {folder_collection_error}"
            ) from folder_collection_error

        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            logger.error("ArangoDB client is not connected", task_id=task_id)
            raise RuntimeError("ArangoDB client is not connected")

        if arangodb_client.db.aql is None:
            logger.error("ArangoDB AQL is not available", task_id=task_id)
            raise RuntimeError("ArangoDB AQL is not available")

        # 修改時間：2025-12-09 - 查詢資料夾（只查詢屬於當前任務的資料夾）
        # 注意：為了支持嵌套資料夾結構（子資料夾的子資料夾），需要遞歸查詢
        # 但首先只查詢屬於當前任務的資料夾（task_id 匹配）
        try:
            aql_query = """
            FOR folder IN folder_metadata
                FILTER folder.user_id == @user_id
                FILTER folder.task_id == @task_id
                RETURN folder
            """
            cursor = arangodb_client.db.aql.execute(
                aql_query,
                bind_vars={
                    "user_id": effective_user_id,
                    "task_id": task_id,
                },
            )
            all_folders = list(cursor) if cursor else []  # type: ignore[arg-type]  # 同步模式下 Cursor 可迭代
        except Exception as aql_error:
            logger.error(
                "Failed to query folders",
                error=str(aql_error),
                task_id=task_id,
                user_id=effective_user_id,
                exc_info=True,
            )
            # 如果查詢失敗，返回空列表而不是拋出異常
            all_folders = []

        # 按任務ID組織文件樹
        # 修改時間：2025-01-27 - 移除 temp-workspace，所有文件必須關聯到任務工作區
        # 文件應該顯示在「任務工作區」資料夾下，而不是直接在任務下
        tree: dict = {}

        # 先添加資料夾（作為任務節點），使用資料夾的 _key 作為節點ID
        for folder_doc in all_folders:
            folder_task_id = folder_doc.get("task_id")
            folder_key = folder_doc.get("_key")
            # 只添加屬於當前任務的資料夾
            if folder_task_id == task_id and folder_key:
                if folder_key not in tree:
                    tree[folder_key] = []
                # 資料夾本身不作為文件添加，只作為任務節點存在

        # 確保任務工作區節點存在（如果還沒有添加）
        workspace_key = f"{task_id}_workspace"
        if workspace_key not in tree:
            tree[workspace_key] = []

        # 修改時間：2025-12-09 - 根據 file_metadata.folder_id 將文件添加到對應的資料夾
        # 如果 folder_id 為 None 或不存在，則添加到任務工作區
        # 修改時間：2026-01-05 - 添加去重邏輯，避免重複文件顯示
        seen_file_ids: set[str] = set()
        for file_metadata in all_files:
            if file_metadata.task_id == task_id:
                file_id = file_metadata.file_id
                # 跳過重複的文件（按 file_id 去重）
                if file_id in seen_file_ids:
                    logger.warning(
                        "Duplicate file found in file tree",
                        file_id=file_id,
                        filename=file_metadata.filename,
                        task_id=task_id,
                    )
                    continue
                seen_file_ids.add(file_id)

                # 獲取文件的 folder_id，如果沒有則使用 workspace_key
                folder_id = getattr(file_metadata, "folder_id", None) or workspace_key
                # 確保資料夾節點存在
                if folder_id not in tree:
                    tree[folder_id] = []
                tree[folder_id].append(file_metadata.model_dump(mode="json"))

        # 計算總任務數（包括有文件的任務和有資料夾但沒有文件的任務）
        # 修改時間：2025-01-27 - 移除 temp-workspace 相關邏輯
        total_tasks = len(tree)

        # 構建資料夾信息映射（用於前端顯示資料夾名稱）
        # 修改時間：2025-01-27 - 添加 folder_type 以支持區分任務工作區和排程任務
        # 修改時間：2025-12-09 - 確保任務工作區和排程任務資料夾也被包含
        folders_info = {}
        for folder_doc in all_folders:
            folder_key = folder_doc.get("_key")
            if folder_key:
                folders_info[folder_key] = {
                    "folder_name": folder_doc.get("folder_name", folder_key),
                    "parent_task_id": folder_doc.get("parent_task_id"),
                    "user_id": folder_doc.get("user_id"),
                    "folder_type": folder_doc.get("folder_type"),  # 添加 folder_type
                    "task_id": folder_doc.get("task_id"),  # 添加 task_id
                }

        # 確保任務工作區和排程任務資料夾也被包含（即使它們還沒有被創建）
        workspace_key = f"{task_id}_workspace"
        scheduled_key = f"{task_id}_scheduled"
        if workspace_key not in folders_info:
            folders_info[workspace_key] = {
                "folder_name": "任務工作區",
                "parent_task_id": None,
                "user_id": effective_user_id,
                "folder_type": "workspace",
                "task_id": task_id,
            }
        if scheduled_key not in folders_info:
            folders_info[scheduled_key] = {
                "folder_name": "排程任務",
                "parent_task_id": None,
                "user_id": effective_user_id,
                "folder_type": "scheduled",
                "task_id": task_id,
            }

        logger.info(
            "File tree query completed",
            task_id=task_id,
            total_folders=len(all_folders),
            folders_info_count=len(folders_info),
            folders_info=folders_info,
        )

        return APIResponse.success(
            data={
                "tree": tree,
                "folders": folders_info,  # 添加資料夾信息
                "total_tasks": total_tasks,
                "total_files": len(all_files),
            },
            message="文件樹查詢成功",
        )
    except Exception as e:
        logger.error("Failed to get file tree", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"查詢文件樹失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/tree/{task_id}/validate")
async def validate_file_tree(
    task_id: str, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """驗證文件樹與檔案系統一致性"""
    try:
        # 修改時間：2025-12-09 - 檢查任務是否屬於當前用戶
        permission_service = get_file_permission_service()
        if not permission_service.check_task_file_access(
            user=current_user,
            task_id=task_id,
            required_permission=Permission.FILE_READ.value,
        ):
            return APIResponse.error(
                message=f"任務 {task_id} 不存在或不屬於當前用戶",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        sync_service = get_file_tree_sync_service()
        result = sync_service.validate_file_tree(user_id=current_user.user_id, task_id=task_id)
        return APIResponse.success(data=result, message="文件樹驗證完成")
    except Exception as e:
        logger.error("Failed to validate file tree", task_id=task_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"文件樹驗證失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/tree/{task_id}/sync")
async def sync_file_tree(
    task_id: str, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """構建並同步文件樹到 user_tasks"""
    try:
        # 修改時間：2025-12-09 - 檢查任務是否屬於當前用戶
        permission_service = get_file_permission_service()
        if not permission_service.check_task_file_access(
            user=current_user,
            task_id=task_id,
            required_permission=Permission.FILE_UPDATE.value,
        ):
            return APIResponse.error(
                message=f"任務 {task_id} 不存在或不屬於當前用戶",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        sync_service = get_file_tree_sync_service()
        result = sync_service.sync_file_tree(user_id=current_user.user_id, task_id=task_id)
        return APIResponse.success(data=result, message="文件樹同步完成")
    except Exception as e:
        logger.error("Failed to sync file tree", task_id=task_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"文件樹同步失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/tree/{task_id}/version")
async def get_file_tree_version(
    task_id: str, current_user: User = Depends(get_current_user)
) -> JSONResponse:
    """查詢文件樹版本資訊"""
    try:
        # 修改時間：2025-12-09 - 檢查任務是否屬於當前用戶
        permission_service = get_file_permission_service()
        if not permission_service.check_task_file_access(
            user=current_user,
            task_id=task_id,
            required_permission=Permission.FILE_READ.value,
        ):
            return APIResponse.error(
                message=f"任務 {task_id} 不存在或不屬於當前用戶",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        sync_service = get_file_tree_sync_service()
        result = sync_service.get_file_tree_version(user_id=current_user.user_id, task_id=task_id)
        return APIResponse.success(data=result, message="文件樹版本查詢成功")
    except Exception as e:
        logger.error(
            "Failed to get file tree version",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"文件樹版本查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{file_id}/download", response_model=None)
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def download_file(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> Union[FileResponse, StreamingResponse, JSONResponse]:
    """下載文件

    修改時間：2026-01-05 - 支持 SeaWeedFS 和本地文件系統，使用統一的 read_file 方法

    Args:
        file_id: 文件ID
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        文件響應
    """
    try:
        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_DOWNLOAD.value,
        )

        storage = get_storage()
        metadata_service = get_metadata_service()

        # 獲取文件元數據（用於獲取 task_id 和 storage_path）
        metadata = metadata_service.get(file_id)
        if not metadata:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "文件元數據不存在"},
            )

        filename = metadata.filename if metadata else file_id

        # 修改時間：2026-01-05 - 優化大文件下載，避免超時
        # 對於本地文件系統，直接使用 FileResponse（最有效率）
        # 對於 SeaWeedFS/S3，使用流式讀取

        # 修改時間：2026-01-05 - 優先檢查 metadata.storage_path 是否為本地路徑
        # 如果 storage_path 是本地路徑（不以 s3:// 開頭），即使使用 S3FileStorage，也應該從本地讀取
        local_file_path = None
        if metadata.storage_path and not metadata.storage_path.startswith("s3://"):
            # 這是本地路徑，檢查文件是否存在
            if os.path.exists(metadata.storage_path):
                local_file_path = metadata.storage_path
            else:
                # 嘗試相對路徑（從項目根目錄）
                possible_paths = [
                    metadata.storage_path,
                    f"./{metadata.storage_path}",
                    os.path.join(os.getcwd(), metadata.storage_path),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        local_file_path = path
                        break

        # 如果找到本地文件，直接使用 FileResponse
        if local_file_path:
            try:
                logger.debug(
                    "Using local file path for download",
                    file_id=file_id,
                    local_file_path=local_file_path,
                )
                return FileResponse(
                    path=local_file_path,
                    filename=filename,
                    media_type="application/octet-stream",
                )
            except Exception as e:
                logger.warning(
                    "Failed to use FileResponse with local path, falling back to streaming",
                    file_id=file_id,
                    local_file_path=local_file_path,
                    error=str(e),
                )

        # 嘗試從存儲後端獲取文件路徑
        file_path = storage.get_file_path(
            file_id=file_id,
            task_id=metadata.task_id,
            metadata_storage_path=metadata.storage_path,
        )

        # 如果是本地文件系統且文件存在，直接使用 FileResponse（流式傳輸，不佔用內存）
        if file_path and os.path.exists(file_path):
            try:
                return FileResponse(
                    path=file_path,
                    filename=filename,
                    media_type="application/octet-stream",
                )
            except Exception as e:
                logger.warning(
                    "Failed to use FileResponse, falling back to streaming",
                    file_id=file_id,
                    file_path=file_path,
                    error=str(e),
                )

        # 對於 SeaWeedFS/S3 或本地文件不存在的情況，使用流式讀取
        # 修改時間：2026-01-05 - 使用生成器實現流式傳輸，避免一次性加載整個文件到內存
        async def file_stream_generator():
            """流式讀取文件內容的生成器"""
            try:
                # 檢查是否為 S3/SeaWeedFS 存儲
                from storage.s3_storage import S3FileStorage

                if isinstance(storage, S3FileStorage):
                    # 對於 S3/SeaWeedFS，使用流式讀取（避免一次性加載整個文件）
                    try:
                        # 獲取 S3 URI
                        s3_uri = metadata.storage_path or storage.get_file_path(
                            file_id=file_id,
                            task_id=metadata.task_id,
                            metadata_storage_path=metadata.storage_path,
                        )

                        if s3_uri:
                            parsed = storage._parse_s3_uri(s3_uri)  # type: ignore[attr-defined]
                            if parsed:
                                bucket, key = parsed
                                # 使用 boto3 的流式讀取
                                # 修改時間：2026-01-05 - 添加詳細日誌和錯誤處理
                                logger.debug(
                                    "Attempting to stream file from SeaWeedFS",
                                    file_id=file_id,
                                    bucket=bucket,
                                    key=key,
                                    s3_uri=s3_uri,
                                )
                                try:
                                    response = storage.s3_client.get_object(  # type: ignore[attr-defined]
                                        Bucket=bucket, Key=key
                                    )
                                    # 流式讀取，每次讀取 8KB
                                    chunk_size = 8192
                                    body = response["Body"]
                                    bytes_read = 0
                                    while True:
                                        chunk = body.read(chunk_size)
                                        if not chunk:
                                            break
                                        bytes_read += len(chunk)
                                        yield chunk
                                    logger.debug(
                                        "Successfully streamed file from SeaWeedFS",
                                        file_id=file_id,
                                        bytes_read=bytes_read,
                                    )
                                    return
                                except ConnectionClosedError as conn_err:
                                    # 連接關閉錯誤，可能是文件不存在或 SeaWeedFS 問題
                                    logger.error(
                                        "SeaWeedFS connection closed",
                                        file_id=file_id,
                                        bucket=bucket,
                                        key=key,
                                        error=str(conn_err),
                                    )
                                    # 重新拋出，讓外層處理
                                    raise
                    except Exception as e:
                        # 修改時間：2026-01-05 - 詳細記錄錯誤，便於調試
                        error_msg = str(e)
                        error_type = type(e).__name__

                        # 檢查是否為連接錯誤（SeaWeedFS 服務未運行）
                        is_connection_error = (
                            "Connection" in error_type
                            or "connection" in error_msg.lower()
                            or "refused" in error_msg.lower()
                            or "closed" in error_msg.lower()
                        )

                        logger.warning(
                            "Failed to stream from S3/SeaWeedFS",
                            file_id=file_id,
                            error=error_msg,
                            error_type=error_type,
                            s3_uri=s3_uri if "s3_uri" in locals() else None,
                            is_connection_error=is_connection_error,
                        )

                        # 如果是連接錯誤，直接拋出異常，不嘗試回退（因為文件在 SeaWeedFS 中）
                        if is_connection_error:
                            endpoint = getattr(storage, "endpoint", "unknown")  # type: ignore[attr-defined]
                            raise RuntimeError(
                                f"SeaWeedFS 服務連接失敗，無法讀取文件。"
                                f"請檢查 SeaWeedFS 服務是否運行（端點: {endpoint}）。"
                                f"錯誤詳情: {error_msg}"
                            ) from e

                        # 其他錯誤繼續嘗試回退

                # 如果無法流式讀取，嘗試使用 read_file（對於小文件）
                file_content = None
                try:
                    file_content = storage.read_file(  # type: ignore[call-arg]
                        file_id=file_id,
                        task_id=metadata.task_id,
                        metadata_storage_path=metadata.storage_path,
                    )
                except TypeError:
                    # 向後兼容：如果 storage 不支持額外參數
                    file_content = storage.read_file(file_id)

                # 如果無法從存儲讀取，嘗試從本地文件系統讀取（向後兼容）
                if file_content is None and file_path and os.path.exists(file_path):
                    try:
                        # 使用分塊讀取，避免一次性加載大文件
                        chunk_size = 8192  # 8KB chunks
                        with open(file_path, "rb") as f:
                            while True:
                                chunk = f.read(chunk_size)
                                if not chunk:
                                    break
                                yield chunk
                        return
                    except Exception as e:
                        logger.warning(
                            "Failed to read file from local path",
                            file_id=file_id,
                            file_path=file_path,
                            error=str(e),
                        )

                # 如果已經讀取到內容，分塊返回（避免一次性返回大文件）
                if file_content:
                    chunk_size = 8192  # 8KB chunks
                    for i in range(0, len(file_content), chunk_size):
                        yield file_content[i : i + chunk_size]
                else:
                    raise ValueError("文件不存在或無法讀取")

            except Exception as e:
                logger.error(
                    "Failed to stream file",
                    file_id=file_id,
                    error=str(e),
                )
                raise

        # 使用 StreamingResponse 進行流式傳輸
        return StreamingResponse(
            file_stream_generator(),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except Exception as e:
        logger.error("Failed to download file", file_id=file_id, error=str(e), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"下載文件失敗: {str(e)}"},
        )


@router.get("/{file_id}/preview")
async def preview_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """預覽文件（文本文件）

    Args:
        file_id: 文件ID
        current_user: 當前認證用戶

    Returns:
        文件預覽內容
    """
    try:
        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_READ.value,
        )

        if not metadata:
            return APIResponse.error(
                message="文件元數據不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        storage = get_storage()

        # 修改時間：2025-01-27 - 改進文件路徑查找邏輯
        # 優先使用 metadata 中的 storage_path，然後嘗試從 task_id 推斷，最後使用舊結構
        file_path = storage.get_file_path(
            file_id=file_id,
            task_id=metadata.task_id,
            metadata_storage_path=metadata.storage_path,
        )

        # 檢查文件是否存在
        if not file_path or not os.path.exists(file_path):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 只支持文本文件預覽
        text_types = ["text/plain", "text/markdown", "text/csv", "application/json"]
        if metadata.file_type not in text_types:
            return APIResponse.error(
                message="不支持預覽此文件類型",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 讀取文件內容（限制大小，避免內存問題）
        max_preview_size = 100 * 1024  # 100KB
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(max_preview_size)
            is_truncated = os.path.getsize(file_path) > max_preview_size

        return APIResponse.success(
            data={
                "file_id": file_id,
                "filename": metadata.filename,
                "file_type": metadata.file_type,
                "content": content,
                "is_truncated": is_truncated,
                "file_size": metadata.file_size,
            },
            message="文件預覽成功",
        )
    except Exception as e:
        logger.error("Failed to preview file", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"預覽文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{file_id}/rename", response_model=None)
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def rename_file(
    file_id: str,
    request_body: FileRenameRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """重命名文件

    Args:
        file_id: 文件ID
        request_body: 重命名請求體
        current_user: 當前認證用戶

    Returns:
        更新後的文件信息
    """
    try:
        # 檢查文件訪問權限（需要寫入權限）
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_UPDATE.value,
        )

        # 驗證新文件名
        new_name = request_body.new_name.strip()
        if not new_name:
            return APIResponse.error(
                message="文件名不能為空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 使用 FileValidator 驗證文件名
        validator = get_validator()

        # 驗證文件名長度
        if len(new_name) > 255:
            return APIResponse.error(
                message="文件名長度不能超過255個字符",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 驗證文件名路徑（防止路徑遍歷和特殊字符）
        if not validator.validate_path(new_name):
            return APIResponse.error(
                message='文件名包含非法字符（不能包含 / \\ : * ? " < > | 等字符）',
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 驗證文件擴展名（必須包含有效的擴展名）
        from pathlib import Path

        file_ext = Path(new_name).suffix.lower()
        if not file_ext:
            return APIResponse.error(
                message="文件名必須包含有效的文件擴展名",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 檢查擴展名是否在允許列表中
        if file_ext not in validator.allowed_extensions:
            return APIResponse.error(
                message=f"不支持的文件擴展名: {file_ext}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 驗證系統保留名稱（Windows）

        reserved_names = [
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        ]
        name_without_ext = Path(new_name).stem.upper()
        if name_without_ext in reserved_names:
            return APIResponse.error(
                message=f"不能使用系統保留名稱: {name_without_ext}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 更新元數據中的文件名
        # 由於 FileMetadataUpdate 不支持 filename，直接操作數據庫
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = arangodb_client.db.collection("file_metadata")
        file_doc = collection.get(file_id)
        if file_doc is None:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        update_data = {
            "filename": new_name,
            "updated_at": datetime.utcnow().isoformat(),
        }
        # ArangoDB 的 update 方法需要文档对象（dict）作为第一个参数
        file_doc.update(update_data)
        collection.update(file_doc)  # type: ignore[arg-type]  # update 接受 dict

        # 獲取更新後的文件元數據
        updated_doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None
        if updated_doc is None or not isinstance(updated_doc, dict):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        updated_metadata = FileMetadata(**updated_doc)  # type: ignore[arg-type]  # doc 已檢查為 dict

        logger.info(
            "File renamed successfully",
            file_id=file_id,
            old_name=file_metadata.filename,
            new_name=new_name,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data=updated_metadata.model_dump(mode="json"),
            message="文件重命名成功",
        )
    except Exception as e:
        logger.error("Failed to rename file", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"重命名文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{file_id}/copy")
@audit_log(
    action=AuditAction.FILE_CREATE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def copy_file(
    file_id: str,
    request_body: FileCopyRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """複製文件

    Args:
        file_id: 源文件ID
        request_body: 複製請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        新文件的信息
    """
    try:
        # 檢查源文件訪問權限
        permission_service = get_file_permission_service()
        source_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_READ.value,
        )

        storage = get_storage()

        # 檢查源文件是否存在
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="源文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 讀取源文件內容
        file_content = storage.read_file(file_id)
        if file_content is None:
            return APIResponse.error(
                message="無法讀取源文件",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 生成新的文件ID
        new_file_id = FileStorage.generate_file_id()

        # 生成新文件名（添加副本後綴）
        original_filename = source_metadata.filename
        name_parts = os.path.splitext(original_filename)
        new_filename = f"{name_parts[0]}_copy{name_parts[1]}"

        # 保存文件副本
        new_file_id, new_file_path = storage.save_file(
            file_content=file_content,
            filename=new_filename,
            file_id=new_file_id,
        )

        # 創建新的元數據記錄
        metadata_service = get_metadata_service()
        from services.api.models.file_metadata import FileMetadataCreate

        new_metadata = FileMetadataCreate(
            file_id=new_file_id,
            filename=new_filename,
            file_type=source_metadata.file_type,
            file_size=source_metadata.file_size,
            folder_id=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
            storage_path=None,  # type: ignore[call-arg]
            user_id=current_user.user_id,
            task_id=request_body.target_task_id or source_metadata.task_id,
            tags=source_metadata.tags.copy() if source_metadata.tags else [],
            description=source_metadata.description,
            custom_metadata=(
                source_metadata.custom_metadata.copy() if source_metadata.custom_metadata else {}
            ),
            status="uploaded",
            processing_status=None,
            chunk_count=None,
            vector_count=None,
            kg_status=None,
        )

        created_metadata = metadata_service.create(new_metadata)

        logger.info(
            "File copied successfully",
            source_file_id=file_id,
            new_file_id=new_file_id,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data=created_metadata.model_dump(mode="json"),
            message="文件複製成功",
        )
    except Exception as e:
        logger.error("Failed to copy file", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"複製文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{file_id}/move")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: (
        body.get("data", {}).get("file_id") if isinstance(body, dict) else None
    ),
)
async def move_file(
    file_id: str,
    request: Request,
    request_body: FileMoveRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """移動文件（更改所屬任務）

    Args:
        file_id: 文件ID
        request_body: 移動請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        更新後的文件信息
    """
    try:
        # 修改時間：2025-12-08 09:45:47 UTC+8 - 修復請求體解析問題
        # 檢查請求體類型（防止 FastAPI 解析錯誤）
        if not isinstance(request_body, FileMoveRequest):
            logger.error(
                "Invalid request body type for move_file",
                file_id=file_id,
                request_body_type=type(request_body).__name__,
                request_body_repr=str(request_body)[:500],
            )
            # 嘗試手動解析（如果 request_body 是字典）
            if isinstance(request_body, dict):
                try:
                    request_body = FileMoveRequest(**request_body)
                except Exception as parse_error:
                    logger.error(
                        "Failed to parse request body as dict",
                        file_id=file_id,
                        error=str(parse_error),
                    )
                    return APIResponse.error(
                        message=f"無效的請求體格式: {str(parse_error)}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            elif isinstance(request_body, str) and request:
                # 修改時間：2025-12-08 09:45:47 UTC+8 - 處理請求體被解析為字符串的情況
                # 如果請求體是字符串，嘗試從 request.json() 獲取
                logger.warning(
                    "Request body is string, attempting to parse from request.json()",
                    file_id=file_id,
                    request_body_str=request_body,
                )
                try:
                    body_data = await request.json()
                    request_body = FileMoveRequest(**body_data)
                except Exception as parse_error:
                    logger.error(
                        "Failed to parse request body from request.json()",
                        file_id=file_id,
                        error=str(parse_error),
                    )
                    return APIResponse.error(
                        message=f"無效的請求體格式: {str(parse_error)}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return APIResponse.error(
                    message=f"無效的請求體類型: {type(request_body).__name__}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # 檢查文件訪問權限（需要寫入權限）
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_UPDATE.value,
        )

        # 修改時間：2025-01-27 - 移除 temp-workspace，文件必須關聯到任務工作區
        # 驗證目標任務ID
        if not request_body.target_task_id:
            return APIResponse.error(
                message="必須提供目標任務ID，文件必須關聯到任務工作區",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        target_task_id = str(request_body.target_task_id).strip()
        if not target_task_id:
            return APIResponse.error(
                message="目標任務ID不能為空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 修改時間：2025-12-09 - 檢查源任務是否屬於當前用戶
        # 確保用戶只能移動自己任務中的文件
        if file_metadata.task_id:
            from services.api.services.user_task_service import get_user_task_service

            task_service = get_user_task_service()
            source_task = task_service.get(
                user_id=current_user.user_id,
                task_id=file_metadata.task_id,
            )
            if source_task is None:
                return APIResponse.error(
                    message=f"源任務 {file_metadata.task_id} 不存在或不屬於當前用戶",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 驗證目標任務是否存在且屬於當前用戶
        from services.api.services.user_task_service import get_user_task_service

        task_service = get_user_task_service()
        target_task = task_service.get(
            user_id=current_user.user_id,
            task_id=target_task_id,
        )
        if target_task is None:
            return APIResponse.error(
                message="目標任務不存在或不屬於當前用戶",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 驗證目標資料夾（可選）。若未提供，預設為任務工作區
        target_folder_id: Optional[str] = request_body.target_folder_id
        if target_folder_id:
            arangodb_client = get_arangodb_client()
            if arangodb_client.db is None:
                raise RuntimeError("ArangoDB client is not connected")
            folder_col = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
            folder_doc = folder_col.get(target_folder_id)
            if (
                folder_doc is None
                or folder_doc.get("user_id") != current_user.user_id
                or folder_doc.get("task_id") != target_task_id
            ):
                return APIResponse.error(
                    message="目標資料夾不存在或不屬於當前用戶/任務",
                    status_code=status.HTTP_403_FORBIDDEN,
                )
        else:
            target_folder_id = f"{target_task_id}_workspace"

        # 如果目標任務與資料夾都相同，直接返回
        if (
            file_metadata.task_id == target_task_id
            and getattr(file_metadata, "folder_id", None) == target_folder_id
        ):
            return APIResponse.success(
                data=file_metadata.model_dump(mode="json"),
                message="文件已在目標目錄中",
            )

        # 更新元數據中的任務ID（允許設置為 None）
        metadata_service = get_metadata_service()
        from services.api.models.file_metadata import FileMetadataUpdate

        update_data = FileMetadataUpdate(
            task_id=target_task_id,
            folder_id=target_folder_id,
            tags=None,  # type: ignore[call-arg]  # 所有參數都是 Optional
            description=None,  # type: ignore[call-arg]
            custom_metadata=None,  # type: ignore[call-arg]
            status=None,  # type: ignore[call-arg]
            processing_status=None,  # type: ignore[call-arg]
            chunk_count=None,  # type: ignore[call-arg]
            vector_count=None,  # type: ignore[call-arg]
            kg_status=None,  # type: ignore[call-arg]
        )
        updated_metadata = metadata_service.update(file_id, update_data)

        if updated_metadata is None:
            return APIResponse.error(
                message="更新文件元數據失敗",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "File moved successfully",
            file_id=file_id,
            old_task_id=file_metadata.task_id,
            new_task_id=target_task_id,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data=updated_metadata.model_dump(mode="json"),
            message="文件移動成功",
        )
    except Exception as e:
        logger.error("Failed to move file", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"移動文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{file_id}")
@audit_log(
    action=AuditAction.FILE_DELETE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除文件（多數據源清理）

    刪除文件時需要清理以下數據源：
    1. 文件實體（從文件系統）
    2. 文件元數據（從 ArangoDB）
    3. 向量數據（從 ChromaDB）
    4. 知識圖譜關聯（從 ArangoDB）

    Args:
        file_id: 文件ID
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        # 檢查文件訪問權限（需要刪除權限）
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_DELETE.value,
        )

        # 記錄刪除操作的各個步驟結果
        deletion_results = {
            "vector_deleted": False,
            "metadata_deleted": False,
            "file_deleted": False,
            "kg_deleted": False,
        }
        deletion_errors = []

        # 1. 刪除ChromaDB中的向量數據
        try:
            vector_store_service = get_vector_store_service()
            vector_store_service.delete_vectors_by_file_id(
                file_id=file_id, user_id=current_user.user_id
            )
            deletion_results["vector_deleted"] = True
            logger.info("向量數據刪除成功", file_id=file_id)
        except Exception as e:
            error_msg = f"刪除向量數據失敗: {str(e)}"
            deletion_errors.append(error_msg)
            logger.warning(error_msg, file_id=file_id, error=str(e))

        # 2. 刪除知識圖譜關聯（從 ArangoDB 中刪除與該文件相關的實體和關係）
        try:
            arangodb_client = get_arangodb_client()
            if arangodb_client.db is not None and arangodb_client.db.aql is not None:
                # 檢查知識圖譜集合是否存在
                entities_collection = "entities"
                relations_collection = "relations"

                if arangodb_client.db.has_collection(entities_collection):
                    # 刪除與文件相關的實體（假設實體有 file_id 或 file_ids 字段）
                    aql_query_entities = """
                    FOR entity IN entities
                        FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                        REMOVE entity IN entities
                    """
                    try:
                        arangodb_client.db.aql.execute(
                            aql_query_entities, bind_vars={"file_id": file_id}
                        )
                    except Exception as e:
                        logger.warning(
                            "刪除實體時出錯（可能沒有 file_id 字段）",
                            file_id=file_id,
                            error=str(e),
                        )

                if arangodb_client.db.has_collection(relations_collection):
                    # 刪除與文件相關的關係（假設關係有 file_id 或 file_ids 字段）
                    aql_query_relations = """
                    FOR relation IN relations
                        FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                        REMOVE relation IN relations
                    """
                    try:
                        arangodb_client.db.aql.execute(
                            aql_query_relations, bind_vars={"file_id": file_id}
                        )
                    except Exception as e:
                        logger.warning(
                            "刪除關係時出錯（可能沒有 file_id 字段）",
                            file_id=file_id,
                            error=str(e),
                        )

                deletion_results["kg_deleted"] = True
                logger.info("知識圖譜關聯刪除成功", file_id=file_id)
        except Exception as e:
            error_msg = f"刪除知識圖譜關聯失敗: {str(e)}"
            deletion_errors.append(error_msg)
            logger.warning(error_msg, file_id=file_id, error=str(e))
            # 知識圖譜刪除失敗不影響文件刪除，繼續執行

        # 3. 刪除文件元數據
        try:
            metadata_service = get_metadata_service()
            metadata_service.delete(file_id)
            deletion_results["metadata_deleted"] = True
            logger.info("文件元數據刪除成功", file_id=file_id)
        except Exception as e:
            error_msg = f"刪除文件元數據失敗: {str(e)}"
            deletion_errors.append(error_msg)
            logger.error(error_msg, file_id=file_id, error=str(e))
            # 如果元數據刪除失敗，不繼續刪除實際文件
            return APIResponse.error(
                message=f"刪除文件失敗: {error_msg}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 4. 刪除實際文件
        try:
            storage = get_storage()
            storage.delete_file(file_id)
            deletion_results["file_deleted"] = True
            logger.info("文件實體刪除成功", file_id=file_id)
        except Exception as e:
            error_msg = f"刪除文件實體失敗: {str(e)}"
            deletion_errors.append(error_msg)
            logger.error(error_msg, file_id=file_id, error=str(e))
            # 文件實體刪除失敗，但元數據已刪除，記錄警告
            logger.warning("文件元數據已刪除，但文件實體刪除失敗", file_id=file_id, error=str(e))

        # 修改時間：2025-12-08 14:20:00 UTC+8 - 記錄文件刪除操作日誌
        try:
            from services.api.services.operation_log_service import get_operation_log_service

            operation_log_service = get_operation_log_service()

            # 處理文件時間字段
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
                    file_metadata.filename if hasattr(file_metadata, "filename") else file_id
                ),
                operation_type="delete",
                created_at=file_created_at,
                updated_at=file_updated_at,
                deleted_at=datetime.utcnow().isoformat() + "Z",
                notes=f"手動刪除文件，刪除結果: {deletion_results}",
            )
        except Exception as e:
            logger.warning("記錄文件刪除操作日誌失敗", file_id=file_id, error=str(e))

        # 記錄刪除操作結果
        logger.info(
            "File deleted successfully",
            file_id=file_id,
            filename=file_metadata.filename,
            deletion_results=deletion_results,
            deletion_errors=deletion_errors if deletion_errors else None,
            user_id=current_user.user_id,
        )

        # 如果有部分步驟失敗，返回警告信息
        if deletion_errors:
            return APIResponse.success(
                data={
                    "file_id": file_id,
                    "deletion_results": deletion_results,
                    "warnings": deletion_errors,
                },
                message=f"文件已刪除，但有部分數據清理失敗: {', '.join(deletion_errors)}",
            )

        return APIResponse.success(
            data={
                "file_id": file_id,
                "deletion_results": deletion_results,
            },
            message="文件刪除成功",
        )
    except Exception as e:
        logger.error("Failed to delete file", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"刪除文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# 資料夾操作相關常數
FOLDER_COLLECTION_NAME = "folder_metadata"


def _check_folder_name_exists(
    folder_name: str,
    parent_task_id: Optional[str],
    user_id: str,
    exclude_folder_id: Optional[str] = None,
) -> bool:
    """
    檢查資料夾名稱是否已存在

    Args:
        folder_name: 資料夾名稱
        parent_task_id: 父任務ID
        user_id: 用戶ID
        exclude_folder_id: 排除的資料夾ID（用於重命名時排除自己）

    Returns:
        是否存在
    """
    try:
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        arangodb_client.db.collection(FOLDER_COLLECTION_NAME)

        # 查詢同一父資料夾下的其他資料夾
        # 注意：parent_task_id 可能為 None（根節點資料夾）
        if exclude_folder_id:
            if parent_task_id is None:
                # 查詢根節點資料夾（parent_task_id 為 null）
                aql_query = """
                FOR folder IN folder_metadata
                    FILTER folder.user_id == @user_id
                    FILTER folder.parent_task_id == null
                    FILTER folder.folder_name == @folder_name
                    FILTER folder._key != @exclude_folder_id
                    RETURN folder
                """
            else:
                # 查詢指定父資料夾下的資料夾
                aql_query = """
                FOR folder IN folder_metadata
                    FILTER folder.user_id == @user_id
                    FILTER folder.parent_task_id == @parent_task_id
                    FILTER folder.folder_name == @folder_name
                    FILTER folder._key != @exclude_folder_id
                    RETURN folder
                """
            bind_vars = {
                "user_id": user_id,
                "folder_name": folder_name,
                "exclude_folder_id": exclude_folder_id,
            }
            if parent_task_id is not None:
                bind_vars["parent_task_id"] = parent_task_id
        else:
            if parent_task_id is None:
                # 查詢根節點資料夾（parent_task_id 為 null）
                aql_query = """
                FOR folder IN folder_metadata
                    FILTER folder.user_id == @user_id
                    FILTER folder.parent_task_id == null
                    FILTER folder.folder_name == @folder_name
                    RETURN folder
                """
            else:
                # 查詢指定父資料夾下的資料夾
                aql_query = """
                FOR folder IN folder_metadata
                    FILTER folder.user_id == @user_id
                    FILTER folder.parent_task_id == @parent_task_id
                    FILTER folder.folder_name == @folder_name
                    RETURN folder
                """
            bind_vars = {
                "user_id": user_id,
                "folder_name": folder_name,
            }
            if parent_task_id is not None:
                bind_vars["parent_task_id"] = parent_task_id

        cursor = arangodb_client.db.aql.execute(aql_query, bind_vars=bind_vars)  # type: ignore[arg-type]  # bind_vars 類型兼容
        existing_folders = list(cursor) if cursor else []  # type: ignore[arg-type]  # 同步模式下 Cursor 可迭代
        return len(existing_folders) > 0
    except Exception as e:
        logger.warning("檢查資料夾名稱是否存在失敗", error=str(e))
        return False


def _generate_unique_folder_name(
    base_name: str,
    parent_task_id: Optional[str],
    user_id: str,
    exclude_folder_id: Optional[str] = None,
) -> str:
    """
    生成唯一的資料夾名稱，如果名稱已存在，自動添加 (1), (2), (3) 等後綴

    Args:
        base_name: 基礎名稱
        parent_task_id: 父任務ID
        user_id: 用戶ID
        exclude_folder_id: 排除的資料夾ID（用於重命名時排除自己）

    Returns:
        唯一的資料夾名稱
    """
    import re

    # 如果基礎名稱不存在，直接返回
    if not _check_folder_name_exists(base_name, parent_task_id, user_id, exclude_folder_id):
        return base_name

    # 檢查基礎名稱是否已經有 (n) 後綴
    pattern = r"^(.+?)\s*\((\d+)\)$"
    match = re.match(pattern, base_name)

    if match:
        # 如果已經有後綴，提取基礎名稱和數字
        base = match.group(1)
        start_num = int(match.group(2))
    else:
        # 如果沒有後綴，使用原始名稱作為基礎
        base = base_name
        start_num = 0

    # 嘗試添加 (1), (2), (3) 等後綴，直到找到不存在的名稱
    for n in range(start_num + 1, 1000):  # 最多嘗試到 (999)
        new_name = f"{base} ({n})"
        if not _check_folder_name_exists(new_name, parent_task_id, user_id, exclude_folder_id):
            return new_name

    # 如果所有嘗試都失敗，返回帶時間戳的名稱
    import time

    timestamp = int(time.time())
    return f"{base_name} ({timestamp})"


def _validate_folder_name(
    folder_name: str,
    parent_task_id: Optional[str],
    user_id: str,
    exclude_folder_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    驗證資料夾名稱

    Args:
        folder_name: 資料夾名稱
        parent_task_id: 父任務ID（用於唯一性檢查）
        user_id: 用戶ID
        exclude_folder_id: 排除的資料夾ID（用於重命名時排除自己）

    Returns:
        (是否有效, 錯誤消息)
    """
    # 驗證長度
    if len(folder_name) > 255:
        return False, "資料夾名稱長度不能超過255個字符"

    # 驗證特殊字符（使用 FileValidator 的 validate_path 方法）
    validator = get_validator()
    if not validator.validate_path(folder_name):
        return False, '資料夾名稱包含非法字符（不能包含 / \\ : * ? " < > | 等字符）'

    # 驗證系統保留名稱（Windows）

    reserved_names = [
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    ]
    if folder_name.upper() in reserved_names:
        return False, f"不能使用系統保留名稱: {folder_name}"

    # 唯一性檢查：同一父資料夾下不能有重名的資料夾
    # 注意：現在這個檢查只返回是否有效，實際的唯一名稱生成由 _generate_unique_folder_name 處理
    return True, None


def _ensure_folder_collection() -> None:
    """確保資料夾集合存在"""
    arangodb_client = get_arangodb_client()
    if arangodb_client.db is None:
        raise RuntimeError("ArangoDB client is not connected")
    if not arangodb_client.db.has_collection(FOLDER_COLLECTION_NAME):
        arangodb_client.db.create_collection(FOLDER_COLLECTION_NAME)
        # 創建索引
        collection = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
        collection.add_index({"type": "persistent", "fields": ["task_id"]})
        collection.add_index({"type": "persistent", "fields": ["user_id"]})


@router.post("/folders")
@audit_log(
    action=AuditAction.FILE_CREATE,
    resource_type="folder",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def create_folder(
    request_body: FolderCreateRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """創建資料夾（實際上是創建任務）

    Args:
        request_body: 創建資料夾請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        創建的資料夾信息
    """
    try:
        # 確保資料夾集合存在
        _ensure_folder_collection()

        # 驗證資料夾名稱
        folder_name = request_body.folder_name.strip()
        if not folder_name:
            return APIResponse.error(
                message="資料夾名稱不能為空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 使用驗證函數驗證資料夾名稱
        is_valid, error_msg = _validate_folder_name(
            folder_name=folder_name,
            parent_task_id=request_body.parent_task_id,
            user_id=current_user.user_id,
        )

        if not is_valid:
            return APIResponse.error(
                message=error_msg or "資料夾名稱驗證失敗",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 生成唯一的資料夾名稱（如果名稱已存在，自動添加 (1), (2), (3) 等後綴）
        unique_folder_name = _generate_unique_folder_name(
            base_name=folder_name,
            parent_task_id=request_body.parent_task_id,
            user_id=current_user.user_id,
        )

        # 如果名稱被修改，記錄日誌
        if unique_folder_name != folder_name:
            logger.info(
                "Folder name auto-renamed to avoid conflict",
                original_name=folder_name,
                new_name=unique_folder_name,
                parent_task_id=request_body.parent_task_id,
            )

        folder_name = unique_folder_name

        # 生成新的資料夾ID（使用 UUID）
        import uuid

        folder_id = str(uuid.uuid4())

        # 修改時間：2025-12-09 - 從 parent_task_id 提取實際的任務 ID
        # 如果 parent_task_id 是 {task_id}_workspace 格式，提取 task_id
        # 如果 parent_task_id 是 None，則無法確定任務 ID（這種情況不應該發生）
        actual_task_id = None
        if request_body.parent_task_id:
            # 如果 parent_task_id 以 _workspace 或 _scheduled 結尾，提取前面的 task_id
            if request_body.parent_task_id.endswith("_workspace"):
                actual_task_id = request_body.parent_task_id.replace("_workspace", "")
            elif request_body.parent_task_id.endswith("_scheduled"):
                actual_task_id = request_body.parent_task_id.replace("_scheduled", "")
            else:
                # 如果 parent_task_id 是另一個資料夾的 ID，需要查詢該資料夾的 task_id
                arangodb_client = get_arangodb_client()
                if arangodb_client.db is None:
                    raise RuntimeError("ArangoDB client is not connected")

                parent_folder = arangodb_client.db.collection(FOLDER_COLLECTION_NAME).get(
                    request_body.parent_task_id
                )
                if parent_folder:
                    actual_task_id = parent_folder.get("task_id")
                else:
                    # 如果找不到父資料夾，嘗試將 parent_task_id 作為 task_id
                    actual_task_id = request_body.parent_task_id

        if actual_task_id is None:
            return APIResponse.error(
                message="無法確定資料夾所屬的任務，請確保在任務工作區內創建資料夾",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 修改時間：2025-12-09 - 檢查任務是否屬於當前用戶
        permission_service = get_file_permission_service()
        if not permission_service.check_task_file_access(
            user=current_user,
            task_id=actual_task_id,
            required_permission=Permission.FILE_UPDATE.value,
        ):
            return APIResponse.error(
                message=f"任務 {actual_task_id} 不存在或不屬於當前用戶",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 創建資料夾元數據記錄
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
        folder_doc = {
            "_key": folder_id,
            "task_id": actual_task_id,  # 使用實際的任務 ID，而不是新生成的 UUID
            "folder_name": folder_name,
            "user_id": current_user.user_id,
            "parent_task_id": request_body.parent_task_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        collection.insert(folder_doc)

        logger.info(
            "Folder created successfully",
            folder_id=folder_id,
            task_id=actual_task_id,
            folder_name=folder_name,
            parent_task_id=request_body.parent_task_id,
            user_id=current_user.user_id,
            is_root_level=request_body.parent_task_id is None,
        )

        return APIResponse.success(
            data={
                "task_id": folder_id,  # 返回資料夾 ID（用於前端識別）
                "folder_id": folder_id,  # 添加 folder_id 字段
                "folder_name": folder_name,
                "user_id": current_user.user_id,
                "parent_task_id": request_body.parent_task_id,
                "actual_task_id": actual_task_id,  # 添加實際任務 ID（用於調試）
            },
            message="資料夾創建成功",
        )
    except Exception as e:
        logger.error("Failed to create folder", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"創建資料夾失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/folders/{folder_id}")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="folder",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def rename_folder(
    folder_id: str,
    request_body: FolderRenameRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """重命名資料夾

    Args:
        folder_id: 資料夾ID（task_id）
        request_body: 重命名請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        更新後的資料夾信息
    """
    try:
        # 確保資料夾集合存在
        _ensure_folder_collection()

        # 驗證新名稱
        new_name = request_body.new_name.strip()
        if not new_name:
            return APIResponse.error(
                message="資料夾名稱不能為空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 檢查資料夾是否存在並獲取資料夾信息
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
        folder_doc = collection.get(folder_id)

        if folder_doc is None:
            return APIResponse.error(
                message="資料夾不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2025-12-09 - 檢查任務權限（資料夾必須屬於當前用戶的任務）
        folder_task_id = folder_doc.get("task_id")
        if folder_task_id:
            permission_service = get_file_permission_service()
            if not permission_service.check_task_file_access(
                user=current_user,
                task_id=folder_task_id,
                required_permission=Permission.FILE_UPDATE.value,
            ):
                return APIResponse.error(
                    message=f"任務 {folder_task_id} 不存在或不屬於當前用戶",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 修改時間：2025-12-09 - 檢查任務權限（資料夾必須屬於當前用戶的任務）
        folder_task_id = folder_doc.get("task_id")
        if folder_task_id:
            permission_service = get_file_permission_service()
            if not permission_service.check_task_file_access(
                user=current_user,
                task_id=folder_task_id,
                required_permission=Permission.FILE_UPDATE.value,
            ):
                return APIResponse.error(
                    message=f"任務 {folder_task_id} 不存在或不屬於當前用戶",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 檢查權限（只有所有者可以重命名）
        if folder_doc.get("user_id") != current_user.user_id:
            if not current_user.has_permission(Permission.ALL.value):
                return APIResponse.error(
                    message="無權重命名此資料夾",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 使用驗證函數驗證資料夾名稱（排除當前資料夾）
        is_valid, error_msg = _validate_folder_name(
            folder_name=new_name,
            parent_task_id=folder_doc.get("parent_task_id"),
            user_id=current_user.user_id,
            exclude_folder_id=folder_id,
        )

        if not is_valid:
            return APIResponse.error(
                message=error_msg or "資料夾名稱驗證失敗",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 生成唯一的資料夾名稱（如果名稱已存在，自動添加 (1), (2), (3) 等後綴）
        unique_folder_name = _generate_unique_folder_name(
            base_name=new_name,
            parent_task_id=folder_doc.get("parent_task_id"),
            user_id=current_user.user_id,
            exclude_folder_id=folder_id,
        )

        # 如果名稱被修改，記錄日誌
        if unique_folder_name != new_name:
            logger.info(
                "Folder name auto-renamed to avoid conflict",
                folder_id=folder_id,
                original_name=new_name,
                new_name=unique_folder_name,
                parent_task_id=folder_doc.get("parent_task_id"),
            )

        # 保存舊名稱用於日誌
        old_name = folder_doc.get("folder_name")

        # 更新資料夾名稱
        # 將更新數據合併到文檔對象中
        folder_doc["folder_name"] = unique_folder_name
        folder_doc["updated_at"] = datetime.utcnow().isoformat()
        # ArangoDB 的 update 方法需要文档对象（dict）作为第一个参数，且必須包含 _id 或 _key
        collection.update(folder_doc)  # type: ignore[arg-type]  # update 接受 dict

        # 獲取更新後的資料夾信息
        updated_doc = collection.get(folder_id)

        logger.info(
            "Folder renamed successfully",
            folder_id=folder_id,
            old_name=old_name,
            new_name=unique_folder_name,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "task_id": folder_id,
                "folder_name": unique_folder_name,
                "user_id": updated_doc.get("user_id"),
                "parent_task_id": updated_doc.get("parent_task_id"),
            },
            message="資料夾重命名成功",
        )
    except Exception as e:
        logger.error("Failed to rename folder", folder_id=folder_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"重命名資料夾失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.patch("/folders/{folder_id}/move", response_model=None)
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="folder",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def move_folder(
    folder_id: str,
    request_body: FolderMoveRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> Any:
    """移動資料夾（更改父資料夾）

    Args:
        folder_id: 資料夾ID（task_id）
        request_body: 移動請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        更新後的資料夾信息
    """
    try:
        # 確保資料夾集合存在
        _ensure_folder_collection()

        # 檢查資料夾是否存在並獲取資料夾信息
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
        folder_doc = collection.get(folder_id)

        if folder_doc is None:
            return APIResponse.error(
                message="資料夾不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2025-12-09 - 檢查任務權限（資料夾必須屬於當前用戶的任務）
        folder_task_id = folder_doc.get("task_id")
        if folder_task_id:
            permission_service = get_file_permission_service()
            if not permission_service.check_task_file_access(
                user=current_user,
                task_id=folder_task_id,
                required_permission=Permission.FILE_UPDATE.value,
            ):
                return APIResponse.error(
                    message=f"任務 {folder_task_id} 不存在或不屬於當前用戶",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 檢查權限（只有所有者可以移動）
        if folder_doc.get("user_id") != current_user.user_id:
            if not current_user.has_permission(Permission.ALL.value):
                return APIResponse.error(
                    message="無權移動此資料夾",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 檢查是否嘗試移動到自己或子資料夾（防止循環引用）
        target_parent_id = request_body.parent_task_id
        if target_parent_id == folder_id:
            return APIResponse.error(
                message="不能將資料夾移動到自己內部",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 檢查是否嘗試移動到子資料夾（遞歸檢查）
        if target_parent_id:
            # 獲取目標父資料夾
            target_parent_doc = collection.get(target_parent_id)
            if target_parent_doc:
                # 檢查目標父資料夾的 parent_task_id 是否等於當前資料夾ID（防止間接循環）
                current_parent_id = target_parent_doc.get("parent_task_id")
                if current_parent_id == folder_id:
                    return APIResponse.error(
                        message="不能將資料夾移動到其子資料夾中",
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )

        # 更新資料夾的 parent_task_id
        old_parent_id = folder_doc.get("parent_task_id")
        folder_doc["parent_task_id"] = target_parent_id
        folder_doc["updated_at"] = datetime.utcnow().isoformat()

        # ArangoDB 的 update 方法需要文档对象（dict）作为第一个参数
        collection.update(folder_doc)  # type: ignore[arg-type]  # update 接受 dict

        # 獲取更新後的資料夾信息
        updated_doc = collection.get(folder_id)

        logger.info(
            "Folder moved successfully",
            folder_id=folder_id,
            old_parent_id=old_parent_id,
            new_parent_id=target_parent_id,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "task_id": folder_id,
                "folder_name": updated_doc.get("folder_name"),
                "user_id": updated_doc.get("user_id"),
                "parent_task_id": updated_doc.get("parent_task_id"),
            },
            message="資料夾移動成功",
        )
    except Exception as e:
        logger.error("Failed to move folder", folder_id=folder_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"移動資料夾失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/folders/{folder_id}")
@audit_log(
    action=AuditAction.FILE_DELETE,
    resource_type="folder",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除資料夾（級聯刪除該資料夾下的所有文件）

    Args:
        folder_id: 資料夾ID（task_id）
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        # 確保資料夾集合存在
        _ensure_folder_collection()

        # 檢查資料夾是否存在
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        folder_collection = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
        folder_doc = folder_collection.get(folder_id)

        if folder_doc is None:
            return APIResponse.error(
                message="資料夾不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2025-12-09 - 檢查任務權限（資料夾必須屬於當前用戶的任務）
        folder_task_id = folder_doc.get("task_id")
        if folder_task_id:
            permission_service = get_file_permission_service()
            if not permission_service.check_task_file_access(
                user=current_user,
                task_id=folder_task_id,
                required_permission=Permission.FILE_DELETE.value,
            ):
                return APIResponse.error(
                    message=f"任務 {folder_task_id} 不存在或不屬於當前用戶",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 檢查權限（只有所有者可以刪除）
        if folder_doc.get("user_id") != current_user.user_id:
            if not current_user.has_permission(Permission.ALL.value):
                return APIResponse.error(
                    message="無權刪除此資料夾",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 獲取該任務下的所有文件
        metadata_service = get_metadata_service()
        files_in_folder = metadata_service.list(
            user_id=current_user.user_id,
            task_id=folder_id,
            limit=10000,  # 獲取所有文件
        )

        # 刪除該資料夾下的所有文件（重用 file_upload.py 中的刪除邏輯）
        deleted_files = []
        failed_files = []
        storage = get_storage()

        for file_metadata in files_in_folder:
            try:
                file_id = file_metadata.file_id

                # 1. 刪除ChromaDB中的向量
                try:
                    vector_store_service = get_vector_store_service()
                    vector_store_service.delete_vectors_by_file_id(
                        file_id=file_id, user_id=current_user.user_id
                    )
                except Exception as e:
                    logger.warning("刪除向量失敗（繼續刪除文件）", file_id=file_id, error=str(e))

                # 2. 刪除文件元數據
                try:
                    metadata_service.delete(file_id)
                except Exception as e:
                    logger.warning(
                        "刪除文件元數據失敗（繼續刪除文件）",
                        file_id=file_id,
                        error=str(e),
                    )

                # 3. 刪除實際文件
                storage.delete_file(file_id)

                deleted_files.append(file_id)
            except Exception as e:
                logger.error("刪除文件失敗", file_id=file_metadata.file_id, error=str(e))
                failed_files.append(file_metadata.file_id)

        # 刪除資料夾元數據記錄
        folder_collection.delete(folder_id)

        logger.info(
            "Folder deleted successfully",
            folder_id=folder_id,
            deleted_files_count=len(deleted_files),
            failed_files_count=len(failed_files),
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "task_id": folder_id,
                "deleted_files_count": len(deleted_files),
                "failed_files_count": len(failed_files),
                "deleted_files": deleted_files,
                "failed_files": failed_files,
            },
            message=f"資料夾及 {len(deleted_files)} 個文件刪除成功"
            + (f"，{len(failed_files)} 個文件刪除失敗" if failed_files else ""),
        )
    except Exception as e:
        logger.error("Failed to delete folder", folder_id=folder_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"刪除資料夾失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/batch/download")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: (
        body.get("data", {}).get("file_ids", [])[0]
        if body.get("data", {}).get("file_ids")
        else None
    ),
)
async def batch_download_files(
    request_body: BatchDownloadRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """批量下載文件（打包為ZIP）

    Args:
        request_body: 批量下載請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        ZIP文件流
    """
    try:
        file_ids = request_body.file_ids

        if not file_ids or len(file_ids) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "請提供至少一個文件ID"},
            )

        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        storage = get_storage()
        metadata_service = get_metadata_service()

        # 創建ZIP文件在內存中
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            downloaded_count = 0
            failed_files = []

            for file_id in file_ids:
                try:
                    # 檢查文件訪問權限
                    permission_service.check_file_access(
                        user=current_user,
                        file_id=file_id,
                        required_permission=Permission.FILE_DOWNLOAD.value,
                    )

                    # 檢查文件是否存在
                    if not storage.file_exists(file_id):
                        failed_files.append({"file_id": file_id, "error": "文件不存在"})
                        continue

                    # 獲取文件路徑
                    file_path = storage.get_file_path(file_id)
                    if not file_path or not os.path.exists(file_path):
                        failed_files.append({"file_id": file_id, "error": "文件路徑不存在"})
                        continue

                    # 獲取文件名
                    metadata = metadata_service.get(file_id)
                    filename = metadata.filename if metadata else file_id

                    # 讀取文件內容並添加到ZIP
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                        zip_file.writestr(filename, file_content)

                    downloaded_count += 1
                except Exception as e:
                    logger.warning("下載文件失敗", file_id=file_id, error=str(e))
                    failed_files.append({"file_id": file_id, "error": str(e)})
                    continue

        # 準備ZIP文件響應
        zip_buffer.seek(0)

        # 生成ZIP文件名
        zip_filename = f"files-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.zip"

        logger.info(
            "Batch download completed",
            total_files=len(file_ids),
            downloaded_count=downloaded_count,
            failed_count=len(failed_files),
            user_id=current_user.user_id,
        )

        # 返回ZIP文件流
        return StreamingResponse(
            io.BytesIO(zip_buffer.read()),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
            },
        )
    except Exception as e:
        logger.error("Failed to batch download files", error=str(e), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": f"批量下載失敗: {str(e)}"},
        )


@router.post("/{file_id}/attach")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def attach_file_to_chat(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """附加文件到聊天（返回文件摘要用於聊天上下文）

    Args:
        file_id: 文件ID
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        文件摘要信息
    """
    try:
        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_READ.value,
        )

        storage = get_storage()

        # 檢查文件是否存在
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 獲取文件路徑
        file_path = storage.get_file_path(file_id)
        if not file_path or not os.path.exists(file_path):
            return APIResponse.error(
                message="文件路徑不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 讀取文件內容（限制大小，避免內存問題）
        max_summary_size = 10 * 1024  # 10KB 用於摘要
        file_content = ""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    file_content = f.read(max_summary_size)
            except Exception:
                # 如果是二進制文件，返回基本信息
                file_content = ""

        # 構建文件摘要
        summary = {
            "file_id": file_id,
            "filename": file_metadata.filename,
            "file_type": file_metadata.file_type,
            "file_size": file_metadata.file_size,
            "upload_time": (
                file_metadata.upload_time.isoformat()
                if hasattr(file_metadata.upload_time, "isoformat")
                else str(file_metadata.upload_time)
            ),
            "preview": (file_content[:1000] if file_content else None),  # 前1000字符作為預覽
            "description": file_metadata.description,
            "tags": file_metadata.tags or [],
        }

        logger.info(
            "File attached to chat",
            file_id=file_id,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data=summary,
            message="文件已附加到聊天",
        )
    except Exception as e:
        logger.error(
            "Failed to attach file to chat",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"附加文件到聊天失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{file_id}/vectors")
async def get_file_vectors(
    file_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查看文件的向量資料

    Args:
        file_id: 文件ID
        limit: 返回數量限制
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        向量列表和統計信息
    """
    try:
        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_READ.value,
        )

        # 獲取文件元數據（用於驗證文件是否存在於系統中）
        metadata_service = get_metadata_service()
        file_metadata_obj = metadata_service.get(file_id)
        if not file_metadata_obj:
            return APIResponse.error(
                message="文件元數據不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2026-01-05 - 移除文件存在性檢查
        # 向量數據存儲在 ChromaDB 中，與文件存儲無關
        # 不需要檢查文件是否在 SeaWeedFS 或本地文件系統中存在
        # 如果文件元數據存在，就可以查詢向量數據

        # 獲取向量資料
        vector_store_service = get_vector_store_service()

        # 獲取所有向量（不限制數量，因為我們需要統計）
        all_vectors = vector_store_service.get_vectors_by_file_id(
            file_id=file_id,
            user_id=current_user.user_id,
            limit=None,  # 獲取所有向量以進行統計
        )

        # 應用分頁
        total_count = len(all_vectors)
        paginated_vectors = all_vectors[offset : offset + limit]

        # 獲取統計信息
        stats = vector_store_service.get_collection_stats(
            file_id=file_id,
            user_id=current_user.user_id,
        )

        logger.info(
            "Retrieved file vectors",
            file_id=file_id,
            total_count=total_count,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "file_id": file_id,
                "vectors": paginated_vectors,
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "stats": stats,
            },
            message="向量資料查詢成功",
        )
    except Exception as e:
        logger.error("Failed to get file vectors", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"查詢向量資料失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class RegenerateRequest(BaseModel):
    """重新生成請求模型"""

    type: str = Field(..., description="重新生成的類型：'vector' 或 'graph'")


@router.post("/{file_id}/regenerate")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def regenerate_file_data(
    file_id: str,
    request_body: RegenerateRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """重新生成文件的向量或圖譜數據

    Args:
        file_id: 文件ID
        request_body: 重新生成請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        重新生成結果
    """
    try:
        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_UPDATE.value,
        )

        if not file_metadata:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        storage = get_storage()

        # 獲取文件路徑
        # 修改時間：2026-01-03 - 添加錯誤處理，如果S3連接失敗，嘗試使用本地路徑
        try:
            file_path = storage.get_file_path(
                file_id=file_id,
                task_id=file_metadata.task_id,
                metadata_storage_path=file_metadata.storage_path,
            )
        except Exception as e:
            logger.warning(
                "Failed to get file path from storage, trying local path",
                file_id=file_id,
                error=str(e)[:100],
            )
            # 如果S3連接失敗，嘗試構建本地路徑
            if file_metadata.storage_path and not file_metadata.storage_path.startswith("s3://"):
                file_path = file_metadata.storage_path
            else:
                # 構建默認本地路徑
                from pathlib import Path

                base_path = Path("./data/datasets/files")
                if file_metadata.task_id:
                    file_path = str(
                        base_path / file_metadata.task_id / file_id / file_metadata.filename
                    )
                else:
                    file_path = str(base_path / file_id[:2] / file_id / file_metadata.filename)

        if not file_path:
            return APIResponse.error(
                message="無法獲取文件路徑",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 檢查文件是否存在（支持本地路徑和S3 URI）
        if file_path.startswith("s3://"):
            # S3 URI，跳過本地文件檢查（會在後續處理中處理）
            pass
        elif not os.path.exists(file_path):
            return APIResponse.error(
                message="文件路徑不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2026-01-03 - 跳過storage.file_exists檢查，因為：
        # 1. SeaweedFS S3 API連接不穩定，可能導致誤報
        # 2. os.path.exists(file_path)已經足夠驗證文件存在
        # 3. 如果文件路徑存在但實際文件不存在，後續處理會自然失敗

        regenerate_type = request_body.type.lower()

        if regenerate_type == "vector":
            # 重新生成向量：只執行向量化流程（分塊+向量化+存儲），跳過 KG 提取
            try:
                queue = get_task_queue(VECTORIZATION_QUEUE)
                job_timeout = get_worker_job_timeout()
                job = queue.enqueue(
                    process_vectorization_only_task,
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_metadata.file_type,
                    user_id=current_user.user_id,
                    job_timeout=job_timeout,
                )

                # 修改時間：2025-12-12 - 任務入隊後立即寫入處理狀態，讓前端可顯示「向量產生中」
                try:
                    from api.routers.file_upload import _update_processing_status

                    _update_processing_status(
                        file_id=file_id,
                        overall_status="processing",
                        overall_progress=0,
                        vectorization={
                            "status": "pending",
                            "progress": 0,
                            "message": "向量重新生成已提交到隊列",
                            "job_id": job.id,
                        },
                        message="向量重新生成已提交到隊列",
                    )
                except Exception:
                    pass

                logger.info(
                    "File vector regeneration triggered via RQ",
                    file_id=file_id,
                    user_id=current_user.user_id,
                    job_id=job.id,
                    queue=VECTORIZATION_QUEUE,
                )

                return APIResponse.success(
                    data={
                        "file_id": file_id,
                        "type": "vector",
                        "status": "queued",
                        "job_id": job.id,
                    },
                    message="向量重新生成已提交到隊列，處理將在後台進行",
                )
            except Exception as e:
                logger.error(
                    "Failed to enqueue vector regeneration task",
                    file_id=file_id,
                    error=str(e),
                )
                return APIResponse.error(
                    message=f"提交向量重新生成任務失敗: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        elif regenerate_type == "graph":
            # 重新生成圖譜：只觸發知識圖譜提取，嘗試重用已存在的 chunks
            try:
                queue = get_task_queue(KG_EXTRACTION_QUEUE)
                job_timeout = get_worker_job_timeout()
                job = queue.enqueue(
                    process_kg_extraction_only_task,
                    file_id=file_id,
                    file_path=file_path,
                    file_type=file_metadata.file_type,
                    user_id=current_user.user_id,
                    force_rechunk=False,  # 嘗試重用已存在的 chunks
                    job_timeout=job_timeout,
                )

                # 修改時間：2025-12-12 - 任務入隊後立即寫入處理狀態，讓前端可顯示「圖譜產生中」
                try:
                    from api.routers.file_upload import _update_processing_status

                    _update_processing_status(
                        file_id=file_id,
                        overall_status="processing",
                        overall_progress=0,
                        kg_extraction={
                            "status": "pending",
                            "progress": 0,
                            "message": "圖譜重新生成已提交到隊列",
                            "job_id": job.id,
                        },
                        message="圖譜重新生成已提交到隊列",
                    )
                except Exception:
                    pass

                logger.info(
                    "File graph regeneration triggered via RQ",
                    file_id=file_id,
                    user_id=current_user.user_id,
                    job_id=job.id,
                    queue=KG_EXTRACTION_QUEUE,
                )

                return APIResponse.success(
                    data={
                        "file_id": file_id,
                        "type": "graph",
                        "status": "queued",
                        "job_id": job.id,
                    },
                    message="圖譜重新生成已提交到隊列，處理將在後台進行",
                )

            except Exception as e:
                logger.error(
                    "Failed to enqueue graph regeneration task",
                    file_id=file_id,
                    error=str(e),
                    exc_info=True,
                )
                return APIResponse.error(
                    message=f"提交圖譜重新生成任務失敗: {str(e)}",
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            return APIResponse.error(
                message=f"不支持的重新生成類型: {regenerate_type}，支持 'vector' 或 'graph'",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    except Exception as e:
        logger.error(
            "Failed to regenerate file data",
            file_id=file_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"重新生成失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{file_id}/graph")
async def get_file_graph(
    file_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """查看文件的圖譜資料

    Args:
        file_id: 文件ID
        limit: 返回數量限制
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        圖譜節點和邊
    """
    try:
        # 檢查文件訪問權限
        permission_service = get_file_permission_service()
        permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_READ.value,
        )

        # 獲取文件元數據（用於驗證文件是否存在於系統中）
        metadata_service = get_metadata_service()
        file_metadata_obj = metadata_service.get(file_id)
        if not file_metadata_obj:
            return APIResponse.error(
                message="文件元數據不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 修改時間：2026-01-05 - 移除文件存在性檢查
        # 圖譜數據存儲在 ArangoDB 中，與文件存儲無關
        # 不需要檢查文件是否在 SeaWeedFS 或本地文件系統中存在
        # 如果文件元數據存在，就可以查詢圖譜數據

        # 優先從結果文件讀取圖譜數據
        import json
        from typing import Any, Dict, List

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        triples: List[Dict[str, Any]] = []
        kg_stats = {
            "triples_count": 0,
            "entities_count": 0,
            "relations_count": 0,
            "status": "not_processed",
        }

        # 嘗試從結果文件讀取三元組數據
        result_file_found = False
        if file_metadata_obj.task_id:
            try:
                from services.api.services.task_workspace_service import get_task_workspace_service

                workspace_service = get_task_workspace_service()
                workspace_path = workspace_service.get_workspace_path(file_metadata_obj.task_id)

                if workspace_path.exists():
                    # 查找匹配的結果文件：{file_id}_kg_result*.json
                    result_files = list(workspace_path.glob(f"{file_id}_kg_result*.json"))

                    if result_files:
                        # 選擇最新的結果文件（按修改時間排序）
                        latest_result_file = max(result_files, key=lambda p: p.stat().st_mtime)

                        logger.info(
                            "Found KG result file",
                            file_id=file_id,
                            result_file=str(latest_result_file),
                        )

                        # 讀取結果文件
                        with open(latest_result_file, "r", encoding="utf-8") as f:
                            result_data = json.load(f)

                        # 提取三元組
                        extracted_triples = result_data.get("extracted_triples", [])

                        if extracted_triples:
                            # 轉換三元組為 G6 格式
                            # 1. 先提取所有唯一節點（應用 limit 和 offset）
                            node_map: Dict[str, Dict[str, Any]] = {}

                            # 先收集所有節點（不應用 limit，因為需要確保邊的節點都存在）
                            all_nodes_map: Dict[str, Dict[str, Any]] = {}
                            for triple in extracted_triples:
                                subject = triple.get("subject", "")
                                subject_type = triple.get("subject_type", "Unknown")
                                obj = triple.get("object", "")
                                obj_type = triple.get("object_type", "Unknown")

                                # 添加主體節點
                                if subject and subject not in all_nodes_map:
                                    all_nodes_map[subject] = {
                                        "id": subject,
                                        "label": subject,
                                        "name": subject,
                                        "type": subject_type,
                                        "text": subject,
                                    }

                                # 添加客體節點
                                if obj and obj not in all_nodes_map:
                                    all_nodes_map[obj] = {
                                        "id": obj,
                                        "label": obj,
                                        "name": obj,
                                        "type": obj_type,
                                        "text": obj,
                                    }

                            # 應用 limit 和 offset 到節點列表
                            all_nodes_list = list(all_nodes_map.values())
                            paginated_nodes = all_nodes_list[offset : offset + limit]
                            node_map = {node["id"]: node for node in paginated_nodes}

                            # 創建節點 ID 集合，用於過濾邊
                            node_id_set = set(node_map.keys())

                            # 2. 只添加兩端節點都在返回節點列表中的邊
                            edge_id_counter = 0
                            for triple in extracted_triples:
                                subject = triple.get("subject", "")
                                obj = triple.get("object", "")
                                relation = triple.get("relation", "")
                                confidence = triple.get("confidence", 0)

                                # 只添加兩端節點都在返回節點列表中的邊
                                if subject and obj and relation:
                                    if subject in node_id_set and obj in node_id_set:
                                        edges.append(
                                            {
                                                "id": f"edge_{edge_id_counter}",
                                                "source": subject,
                                                "target": obj,
                                                "from": subject,
                                                "to": obj,
                                                "label": relation,
                                                "type": relation,
                                                "relation": relation,
                                                "confidence": confidence,
                                            }
                                        )
                                    edge_id_counter += 1

                                # 只添加兩端節點都在返回節點列表中的三元組
                                if subject in node_id_set and obj in node_id_set:
                                    triples.append(
                                        {
                                            "subject": subject,
                                            "subject_type": subject_type,
                                            "relation": relation,
                                            "object": obj,
                                            "object_type": obj_type,
                                            "confidence": confidence,
                                        }
                                    )

                            # 轉換節點映射為列表
                            nodes = list(node_map.values())

                            # 更新統計信息
                            kg_stats = {
                                "triples_count": len(triples),
                                "entities_count": len(nodes),
                                "relations_count": len(edges),
                                "status": "completed",
                            }

                            result_file_found = True
                            logger.info(
                                "Loaded KG data from result file",
                                file_id=file_id,
                                triples_count=len(triples),
                                nodes_count=len(nodes),
                                edges_count=len(edges),
                            )
            except Exception as e:
                logger.warning(
                    "Failed to load KG data from result file",
                    file_id=file_id,
                    error=str(e),
                )

        # 如果結果文件不存在或讀取失敗，嘗試從 ArangoDB 查詢（保持向後兼容）
        if not result_file_found:
            arangodb_client = get_arangodb_client()
            if arangodb_client.db is not None and arangodb_client.db.aql is not None:
                try:
                    # 查詢與文件相關的實體
                    entities_query = """
                    FOR entity IN entities
                        FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                        LIMIT @offset, @limit
                        RETURN entity
                    """
                    entities_result = list(
                        arangodb_client.db.aql.execute(
                            entities_query,
                            bind_vars={
                                "file_id": file_id,
                                "limit": limit,
                                "offset": offset,
                            },  # type: ignore[arg-type]  # bind_vars 類型兼容
                        )
                        if arangodb_client.db.aql
                        else []  # type: ignore[arg-type]  # Cursor 可迭代
                    )

                    # 收集返回的實體 ID 集合，用於過濾關係
                    entity_ids = {entity.get("_id", "") for entity in entities_result}

                    # 如果沒有實體，直接返回空結果
                    if not entity_ids:
                        logger.info(
                            "No entities found for file",
                            file_id=file_id,
                        )
                        return APIResponse.success(
                            data={
                                "nodes": [],
                                "edges": [],
                                "triples": [],
                                "stats": {
                                    "triples_count": 0,
                                    "entities_count": 0,
                                    "relations_count": 0,
                                    "status": "not_processed",
                                },
                            }
                        )

                    # 查詢與文件相關的關係，但只返回兩端節點都在返回的實體列表中的關係
                    # 修改時間：2026-01-27 - 確保返回的邊只引用返回的節點
                    relations_query = """
                    FOR relation IN relations
                        FILTER (relation.file_id == @file_id OR @file_id IN relation.file_ids)
                        AND relation._from IN @entity_ids
                        AND relation._to IN @entity_ids
                        LIMIT @offset, @limit
                        RETURN relation
                    """
                    relations_result = list(
                        arangodb_client.db.aql.execute(
                            relations_query,
                            bind_vars={
                                "file_id": file_id,
                                "entity_ids": list(entity_ids),
                                "limit": limit,
                                "offset": offset,
                            },  # type: ignore[arg-type]  # bind_vars 類型兼容
                        )
                        if arangodb_client.db.aql
                        else []  # type: ignore[arg-type]  # Cursor 可迭代
                    )

                    # 統計總數
                    entities_count_query = """
                    FOR entity IN entities
                        FILTER entity.file_id == @file_id OR @file_id IN entity.file_ids
                        COLLECT WITH COUNT INTO count
                        RETURN count
                    """
                    entities_count_result = list(
                        arangodb_client.db.aql.execute(
                            entities_count_query, bind_vars={"file_id": file_id}  # type: ignore[arg-type]  # bind_vars 類型兼容
                        )
                        if arangodb_client.db.aql
                        else []  # type: ignore[arg-type]  # Cursor 可迭代
                    )
                    entities_count = entities_count_result[0] if entities_count_result else 0

                    relations_count_query = """
                    FOR relation IN relations
                        FILTER relation.file_id == @file_id OR @file_id IN relation.file_ids
                        COLLECT WITH COUNT INTO count
                        RETURN count
                    """
                    relations_count_result = list(
                        arangodb_client.db.aql.execute(
                            relations_count_query, bind_vars={"file_id": file_id}  # type: ignore[arg-type]  # bind_vars 類型兼容
                        )
                        if arangodb_client.db.aql
                        else []  # type: ignore[arg-type]  # Cursor 可迭代
                    )
                    relations_count = relations_count_result[0] if relations_count_result else 0

                    # 轉換實體為節點格式
                    nodes = []
                    for entity in entities_result:
                        nodes.append(
                            {
                                "id": entity.get("_id", ""),
                                "name": entity.get("name", ""),
                                "type": entity.get("type", ""),
                                "text": entity.get("text", ""),
                            }
                        )

                    # 轉換關係為邊格式
                    edges = []
                    for relation in relations_result:
                        edges.append(
                            {
                                "id": relation.get("_id", ""),
                                "from": relation.get("_from", ""),
                                "to": relation.get("_to", ""),
                                "type": relation.get("type", ""),
                                "confidence": relation.get("confidence", 0),
                                "weight": relation.get("weight", 0),
                            }
                        )

                    # 構建三元組（從實體和關係組合）
                    triples = []
                    for relation in relations_result:
                        # 從關係的_from和_to中提取實體信息
                        from_entity_id = relation.get("_from", "").split("/")[-1]
                        to_entity_id = relation.get("_to", "").split("/")[-1]

                        # 查找對應的實體（需要查詢所有實體以匹配）
                        all_entities_query = """
                        FOR entity IN entities
                            FILTER entity._key == @from_key OR entity._key == @to_key
                            RETURN entity
                        """
                        matching_entities = list(
                            arangodb_client.db.aql.execute(
                                all_entities_query,
                                bind_vars={
                                    "from_key": from_entity_id,
                                    "to_key": to_entity_id,
                                },  # type: ignore[arg-type]  # bind_vars 類型兼容
                            )
                            if arangodb_client.db.aql
                            else []  # type: ignore[arg-type]  # Cursor 可迭代
                        )

                        from_entity = next(
                            (e for e in matching_entities if e.get("_key") == from_entity_id),
                            None,
                        )
                        to_entity = next(
                            (e for e in matching_entities if e.get("_key") == to_entity_id),
                            None,
                        )

                        if from_entity and to_entity:
                            triples.append(
                                {
                                    "subject": from_entity.get("name", ""),
                                    "relation": relation.get("type", ""),
                                    "object": to_entity.get("name", ""),
                                    "confidence": relation.get("confidence", 0),
                                    "context": relation.get("context", ""),
                                }
                            )

                    # 更新統計信息
                    kg_stats = {
                        "triples_count": len(triples),
                        "entities_count": entities_count,
                        "relations_count": relations_count,
                        "status": (
                            "completed"
                            if entities_count > 0 or relations_count > 0
                            else "not_processed"
                        ),
                    }

                except Exception as e:
                    logger.warning(
                        "Failed to query graph data from ArangoDB",
                        file_id=file_id,
                        error=str(e),
                    )
                    # 如果查詢失敗，嘗試從 Redis 獲取統計信息（如果可用）
                    try:
                        from database.redis import get_redis_client

                        redis_client = get_redis_client()
                        status_key = f"processing:status:{file_id}"
                        status_data_str = redis_client.get(status_key)  # type: ignore[arg-type]  # 同步 Redis，返回 Optional[str]

                        if status_data_str:
                            status_data = json.loads(status_data_str)  # type: ignore[arg-type]  # status_data_str 已檢查不為 None，且 decode_responses=True 返回 str
                            kg_extraction = status_data.get("kg_extraction", {})
                            if kg_extraction.get("status") == "completed":
                                kg_stats = {
                                    "triples_count": kg_extraction.get("triples_count", 0),
                                    "entities_count": kg_extraction.get("entities_count", 0),
                                    "relations_count": kg_extraction.get("relations_count", 0),
                                    "status": "completed",
                                }
                    except Exception:
                        pass  # Redis 不可用時忽略

        logger.info(
            "Retrieved file graph data",
            file_id=file_id,
            kg_stats=kg_stats,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "file_id": file_id,
                "nodes": nodes,
                "edges": edges,
                "triples": triples,
                "stats": kg_stats,
                "total": kg_stats.get("triples_count", 0),
                "limit": limit,
                "offset": offset,
            },
            message="圖譜資料查詢成功",
        )
    except Exception as e:
        logger.error("Failed to get file graph", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"查詢圖譜資料失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# 文件庫相關API
LIBRARY_TASK_ID = "library"  # 文件庫的特殊 task_id 標識


@router.post("/library/upload")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: (
        body.get("data", {}).get("file_ids", [])[0]
        if body.get("data", {}).get("file_ids")
        else None
    ),
)
async def upload_from_library(
    request_body: LibraryUploadRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """從文件庫上傳文件到當前任務

    將文件庫中的文件（task_id 為 "library" 或 null）複製到目標任務

    Args:
        request_body: 從文件庫上傳請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        上傳結果
    """
    try:
        file_ids = request_body.file_ids
        target_task_id = request_body.target_task_id

        if not file_ids or len(file_ids) == 0:
            return APIResponse.error(
                message="請提供至少一個文件ID",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        get_metadata_service()
        permission_service = get_file_permission_service()

        uploaded_files = []
        failed_files = []

        for file_id in file_ids:
            try:
                # 檢查文件訪問權限
                file_metadata = permission_service.check_file_access(
                    user=current_user,
                    file_id=file_id,
                    required_permission=Permission.FILE_READ.value,
                )

                # 檢查文件是否在文件庫中（task_id 為 "library" 或 null）
                if file_metadata.task_id not in [None, LIBRARY_TASK_ID, ""]:
                    failed_files.append({"file_id": file_id, "error": "文件不在文件庫中"})
                    continue

                # 重用 copy_file 的邏輯，但直接更新 task_id 而不是創建新文件
                # 更新文件的 task_id 到目標任務
                arangodb_client = get_arangodb_client()
                if arangodb_client.db is None:
                    raise RuntimeError("ArangoDB client is not connected")

                collection = arangodb_client.db.collection("file_metadata")
                file_doc = collection.get(file_id)
                if file_doc is None:
                    failed_files.append({"file_id": file_id, "error": "文件不存在"})
                    continue
                update_data = {
                    "task_id": target_task_id,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                # ArangoDB 的 update 方法需要文档对象（dict）作为第一个参数
                file_doc.update(update_data)
                collection.update(file_doc)  # type: ignore[arg-type]  # update 接受 dict

                # 獲取更新後的文件元數據
                updated_doc = collection.get(file_id)
                if updated_doc is None:
                    failed_files.append({"file_id": file_id, "error": "文件更新失敗"})
                    continue

                if not isinstance(updated_doc, dict):
                    failed_files.append({"file_id": file_id, "error": "文件元數據格式錯誤"})
                    continue
                updated_metadata = FileMetadata(**updated_doc)  # type: ignore[arg-type]  # 已檢查為 dict
                uploaded_files.append(updated_metadata.model_dump(mode="json"))

            except Exception as e:
                logger.warning("從文件庫上傳文件失敗", file_id=file_id, error=str(e))
                failed_files.append({"file_id": file_id, "error": str(e)})

        logger.info(
            "Uploaded files from library",
            target_task_id=target_task_id,
            uploaded_count=len(uploaded_files),
            failed_count=len(failed_files),
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "uploaded": uploaded_files,
                "failed": failed_files,
                "total": len(file_ids),
                "uploaded_count": len(uploaded_files),
                "failed_count": len(failed_files),
            },
            message=f"成功上傳 {len(uploaded_files)} 個文件"
            + (f"，{len(failed_files)} 個文件失敗" if failed_files else ""),
        )
    except Exception as e:
        logger.error("Failed to upload from library", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"從文件庫上傳失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/library/return")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: (
        body.get("data", {}).get("file_ids", [])[0]
        if body.get("data", {}).get("file_ids")
        else None
    ),
)
async def return_to_library(
    request_body: LibraryReturnRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """將文件傳回文件庫

    將當前任務的文件傳回文件庫（更新 task_id 為 "library"）

    Args:
        request_body: 傳回文件庫請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        傳回結果
    """
    try:
        file_ids = request_body.file_ids

        if not file_ids or len(file_ids) == 0:
            return APIResponse.error(
                message="請提供至少一個文件ID",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        get_metadata_service()
        permission_service = get_file_permission_service()

        returned_files = []
        failed_files = []

        for file_id in file_ids:
            try:
                # 檢查文件訪問權限
                permission_service.check_file_access(
                    user=current_user,
                    file_id=file_id,
                    required_permission=Permission.FILE_UPDATE.value,
                )

                # 更新文件的 task_id 為文件庫標識
                arangodb_client = get_arangodb_client()
                if arangodb_client.db is None:
                    raise RuntimeError("ArangoDB client is not connected")

                collection = arangodb_client.db.collection("file_metadata")
                file_doc = collection.get(file_id)
                if file_doc is None:
                    failed_files.append({"file_id": file_id, "error": "文件不存在"})
                    continue
                update_data = {
                    "task_id": LIBRARY_TASK_ID,
                    "updated_at": datetime.utcnow().isoformat(),
                }
                # ArangoDB 的 update 方法需要文档对象（dict）作为第一个参数
                file_doc.update(update_data)
                collection.update(file_doc)  # type: ignore[arg-type]  # update 接受 dict

                # 獲取更新後的文件元數據
                updated_doc = collection.get(file_id)
                if updated_doc is None:
                    failed_files.append({"file_id": file_id, "error": "文件更新失敗"})
                    continue

                if not isinstance(updated_doc, dict):
                    failed_files.append({"file_id": file_id, "error": "文件元數據格式錯誤"})
                    continue
                updated_metadata = FileMetadata(**updated_doc)  # type: ignore[arg-type]  # 已檢查為 dict
                returned_files.append(updated_metadata.model_dump(mode="json"))

            except Exception as e:
                logger.warning("傳回文件庫失敗", file_id=file_id, error=str(e))
                failed_files.append({"file_id": file_id, "error": str(e)})

        logger.info(
            "Returned files to library",
            returned_count=len(returned_files),
            failed_count=len(failed_files),
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "returned": returned_files,
                "failed": failed_files,
                "total": len(file_ids),
                "returned_count": len(returned_files),
                "failed_count": len(failed_files),
            },
            message=f"成功傳回 {len(returned_files)} 個文件到文件庫"
            + (f"，{len(failed_files)} 個文件失敗" if failed_files else ""),
        )
    except Exception as e:
        logger.error("Failed to return to library", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"傳回文件庫失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/sync")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("task_id"),
)
async def sync_files(
    request_body: SyncFilesRequest = Body(...),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """同步文件狀態和元數據

    同步文件狀態（處理狀態、向量化狀態等）、元數據和完整性

    Args:
        request_body: 同步文件請求體
        request: FastAPI Request對象
        current_user: 當前認證用戶

    Returns:
        同步結果
    """
    try:
        task_id = request_body.task_id
        file_ids = request_body.file_ids

        if not task_id and not file_ids:
            return APIResponse.error(
                message="請提供任務ID或文件ID列表",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        metadata_service = get_metadata_service()
        storage = get_storage()
        vector_store_service = get_vector_store_service()

        # 獲取要同步的文件列表
        files_to_sync = []
        if file_ids:
            for file_id in file_ids:
                metadata = metadata_service.get(file_id)
                if metadata:
                    files_to_sync.append(metadata)
        elif task_id:
            files_to_sync = metadata_service.list(
                user_id=current_user.user_id,
                task_id=task_id,
                limit=10000,
            )

        sync_results = []

        for file_metadata in files_to_sync:
            file_id = file_metadata.file_id
            sync_result: Dict[str, Any] = {
                "file_id": file_id,
                "filename": file_metadata.filename,
                "status": "success",
                "checks": {
                    "file_exists": False,
                    "metadata_exists": True,
                    "vector_exists": False,
                },
                "updates": [],
            }

            # 檢查文件實體是否存在
            if storage.file_exists(file_id):
                sync_result["checks"]["file_exists"] = True
            else:
                sync_result["status"] = "warning"
                sync_result["updates"].append("文件實體不存在")

            # 檢查向量數據是否存在
            vector_count = 0
            try:
                vectors = vector_store_service.get_vectors_by_file_id(
                    file_id=file_id,
                    user_id=current_user.user_id,
                    limit=1,
                )
                if vectors and len(vectors) > 0:
                    sync_result["checks"]["vector_exists"] = True
                    vector_count = len(vectors)
            except Exception as e:
                logger.warning("檢查向量數據失敗", file_id=file_id, error=str(e))

            # 更新文件元數據中的狀態（如果需要）
            arangodb_client = get_arangodb_client()
            if arangodb_client.db is not None:
                collection = arangodb_client.db.collection("file_metadata")
                file_doc = collection.get(file_id)
                if file_doc:
                    update_data: Dict[str, Any] = {
                        "updated_at": datetime.utcnow().isoformat(),
                    }

                    # 更新向量狀態
                    if sync_result["checks"]["vector_exists"]:
                        update_data["vector_count"] = int(vector_count)

                    # ArangoDB 的 update 方法需要文档对象（dict）作为第一个参数
                    if not isinstance(file_doc, dict):
                        continue
                    file_doc.update(update_data)
                    collection.update(file_doc)  # type: ignore[arg-type]  # 已檢查為 dict
                    sync_result["updates"].append("元數據已更新")

            sync_results.append(sync_result)

        logger.info(
            "Synced files",
            task_id=task_id,
            file_count=len(sync_results),
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "synced": sync_results,
                "total": len(sync_results),
            },
            message=f"成功同步 {len(sync_results)} 個文件",
        )
    except Exception as e:
        logger.error("Failed to sync files", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"同步文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/library/search")
async def search_library(
    query: str = Query(..., description="搜尋關鍵詞"),
    page: int = Query(1, ge=1, description="頁碼"),
    limit: int = Query(20, ge=1, le=100, description="每頁數量"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """搜尋文件庫

    在文件庫中搜尋文件（task_id 為 "library" 或 null）

    Args:
        query: 搜尋關鍵詞
        page: 頁碼
        limit: 每頁數量
        current_user: 當前認證用戶

    Returns:
        搜尋結果列表
    """
    try:
        if not query or not query.strip():
            return APIResponse.error(
                message="請提供搜尋關鍵詞",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        metadata_service = get_metadata_service()

        # 查詢文件庫中的文件（task_id 為 "library" 或 null）
        # 使用 list 方法並過濾
        all_files = metadata_service.list(
            user_id=current_user.user_id,
            task_id=None,  # 查詢所有文件
            limit=10000,
        )

        # 過濾出文件庫中的文件（task_id 為 "library" 或 null）
        library_files = [f for f in all_files if f.task_id in [None, LIBRARY_TASK_ID, ""]]

        # 實現文件名搜尋（簡單的字符串匹配）
        query_lower = query.lower().strip()
        matched_files = [f for f in library_files if query_lower in f.filename.lower()]

        # 分頁
        offset = (page - 1) * limit
        paginated_files = matched_files[offset : offset + limit]

        logger.info(
            "Searched library",
            query=query,
            total_results=len(matched_files),
            page=page,
            limit=limit,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "files": [f.model_dump(mode="json") for f in paginated_files],
                "total": len(matched_files),
                "page": page,
                "limit": limit,
                "total_pages": (len(matched_files) + limit - 1) // limit,
            },
            message=f"找到 {len(matched_files)} 個文件",
        )
    except Exception as e:
        logger.error("Failed to search library", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"搜尋文件庫失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
