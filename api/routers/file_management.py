# 代碼功能說明: 文件管理路由
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-07

"""文件管理路由 - 提供文件列表查詢、搜索、下載、預覽等功能"""

from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from fastapi import APIRouter, Query, status, Depends, Body
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import structlog
import os
import zipfile
import io
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from services.api.services.file_metadata_service import FileMetadataService
from services.api.models.file_metadata import FileMetadata
from system.security.dependencies import get_current_user
from system.security.models import User, Permission
from system.security.audit_decorator import audit_log
from services.api.models.audit_log import AuditAction
from fastapi import Request
from storage.file_storage import FileStorage, create_storage_from_config
from system.infra.config.config import get_config_section
from services.api.services.vector_store_service import get_vector_store_service
from services.api.services.file_permission_service import get_file_permission_service
from services.api.utils.file_validator import (
    FileValidator,
    create_validator_from_config,
)
from database.arangodb import ArangoDBClient

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


class FolderCreateRequest(BaseModel):
    """創建資料夾請求模型"""

    folder_name: str = Field(..., description="資料夾名稱", min_length=1, max_length=255)
    parent_task_id: Optional[str] = Field(None, description="父任務ID（可選）")


class FolderRenameRequest(BaseModel):
    """重命名資料夾請求模型"""

    new_name: str = Field(..., description="新資料夾名稱", min_length=1, max_length=255)


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

    Returns:
        文件列表
    """
    try:
        # 如果未提供user_id，使用當前用戶ID
        if user_id is None:
            user_id = current_user.user_id

        # 如果查詢其他用戶的文件，檢查權限
        if user_id != current_user.user_id:
            get_file_permission_service()
            if not current_user.has_permission(Permission.ALL.value):
                # 非管理員只能查看自己的文件
                user_id = current_user.user_id

        service = get_metadata_service()
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
        results = service.search(
            query=query, user_id=user_id, file_type=file_type, limit=limit
        )

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

        # 獲取所有文件（如果指定了task_id則過濾）
        all_files = service.list(
            user_id=effective_user_id,
            task_id=task_id,
            limit=1000,  # 獲取更多文件以構建樹結構
        )

        # 獲取所有資料夾（如果指定了task_id則過濾父資料夾）
        # 確保資料夾集合存在
        _ensure_folder_collection()
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        arangodb_client.db.collection(FOLDER_COLLECTION_NAME)

        # 查詢資料夾（查詢所有資料夾，由前端根據 parent_task_id 組織樹結構）
        # 注意：為了支持嵌套資料夾結構（子資料夾的子資料夾），需要查詢所有資料夾
        # 前端會根據 parent_task_id 來組織樹結構
        aql_query = """
        FOR folder IN folder_metadata
            FILTER folder.user_id == @user_id
            RETURN folder
        """
        cursor = arangodb_client.db.aql.execute(
            aql_query,
            bind_vars={
                "user_id": effective_user_id,
            },
        )

        all_folders = list(cursor)

        # 按任務ID組織文件樹
        # 如果指定了 task_id，將該任務的文件都歸類到 "temp-workspace"（任務工作區）
        # 如果未指定 task_id，按任務ID組織成樹結構
        tree: dict = {}

        # 先添加資料夾（作為任務節點）
        for folder_doc in all_folders:
            folder_task_id = folder_doc.get("task_id")
            if folder_task_id:
                if folder_task_id not in tree:
                    tree[folder_task_id] = []
                # 資料夾本身不作為文件添加，只作為任務節點存在

        # 添加文件
        for file_metadata in all_files:
            if task_id:
                # 指定了 task_id，將該任務的所有文件都歸類到 "temp-workspace"（任務工作區）
                # 這樣前端就不會看到任務ID的資料夾，只會看到任務工作區
                task_key = "temp-workspace"
            else:
                # 未指定 task_id，將 None 轉換為 "temp-workspace"，其他任務ID保持原樣
                task_key = file_metadata.task_id or "temp-workspace"

            if task_key not in tree:
                tree[task_key] = []
            tree[task_key].append(file_metadata.model_dump(mode="json"))

        # 計算總任務數（包括有文件的任務和有資料夾但沒有文件的任務）
        total_tasks = len(tree)

        # 構建資料夾信息映射（用於前端顯示資料夾名稱）
        folders_info = {}
        for folder_doc in all_folders:
            folder_task_id = folder_doc.get("task_id")
            if folder_task_id:
                folders_info[folder_task_id] = {
                    "folder_name": folder_doc.get("folder_name", folder_task_id),
                    "parent_task_id": folder_doc.get("parent_task_id"),
                    "user_id": folder_doc.get("user_id"),
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


@router.get("/{file_id}/download")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def download_file(
    file_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """下載文件

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

        # 檢查文件是否存在
        if not storage.file_exists(file_id):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "文件不存在"},
            )

        # 獲取文件路徑
        file_path = storage.get_file_path(file_id)
        if not file_path or not os.path.exists(file_path):
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"success": False, "message": "文件路徑不存在"},
            )

        # 獲取文件名
        metadata_service = get_metadata_service()
        metadata = metadata_service.get(file_id)
        filename = metadata.filename if metadata else file_id

        # 返回文件
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream",
        )
    except Exception as e:
        logger.error(
            "Failed to download file", file_id=file_id, error=str(e), exc_info=True
        )
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

        if not metadata:
            return APIResponse.error(
                message="文件元數據不存在",
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
        logger.error(
            "Failed to preview file", file_id=file_id, error=str(e), exc_info=True
        )
        return APIResponse.error(
            message=f"預覽文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{file_id}/rename")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def rename_file(
    file_id: str,
    request_body: FileRenameRequest = Body(...),
    request: Request = None,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """重命名文件

    Args:
        file_id: 文件ID
        request_body: 重命名請求體
        request: FastAPI Request對象
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
        collection.update(file_doc)

        # 獲取更新後的文件元數據
        updated_doc = collection.get(file_id)
        if updated_doc is None:
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        updated_metadata = FileMetadata(**updated_doc)

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
        logger.error(
            "Failed to rename file", file_id=file_id, error=str(e), exc_info=True
        )
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
    request: Request = None,
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
            user_id=current_user.user_id,
            task_id=request_body.target_task_id or source_metadata.task_id,
            tags=source_metadata.tags.copy() if source_metadata.tags else [],
            description=source_metadata.description,
            custom_metadata=source_metadata.custom_metadata.copy()
            if source_metadata.custom_metadata
            else {},
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
        logger.error(
            "Failed to copy file", file_id=file_id, error=str(e), exc_info=True
        )
        return APIResponse.error(
            message=f"複製文件失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{file_id}/move")
@audit_log(
    action=AuditAction.FILE_UPDATE,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_id"),
)
async def move_file(
    file_id: str,
    request_body: FileMoveRequest = Body(...),
    request: Request = None,
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
        # 檢查文件訪問權限（需要寫入權限）
        permission_service = get_file_permission_service()
        file_metadata = permission_service.check_file_access(
            user=current_user,
            file_id=file_id,
            required_permission=Permission.FILE_UPDATE.value,
        )

        # 驗證目標任務ID
        target_task_id = (
            request_body.target_task_id.strip() if request_body.target_task_id else None
        )
        if not target_task_id:
            return APIResponse.error(
                message="目標任務ID不能為空",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 如果目標任務ID與當前相同，直接返回
        if file_metadata.task_id == target_task_id:
            return APIResponse.success(
                data=file_metadata.model_dump(mode="json"),
                message="文件已在目標任務中",
            )

        # 更新元數據中的任務ID
        metadata_service = get_metadata_service()
        from services.api.models.file_metadata import FileMetadataUpdate

        update_data = FileMetadataUpdate(task_id=target_task_id)
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
        logger.error(
            "Failed to move file", file_id=file_id, error=str(e), exc_info=True
        )
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
    request: Request = None,
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
                            "刪除實體時出錯（可能沒有 file_id 字段）", file_id=file_id, error=str(e)
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
                            "刪除關係時出錯（可能沒有 file_id 字段）", file_id=file_id, error=str(e)
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
        logger.error(
            "Failed to delete file", file_id=file_id, error=str(e), exc_info=True
        )
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

        cursor = arangodb_client.db.aql.execute(aql_query, bind_vars=bind_vars)
        existing_folders = list(cursor)
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
    if not _check_folder_name_exists(
        base_name, parent_task_id, user_id, exclude_folder_id
    ):
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
        if not _check_folder_name_exists(
            new_name, parent_task_id, user_id, exclude_folder_id
        ):
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
    request: Request = None,
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

        # 生成新的任務ID（資料夾ID）
        import uuid

        task_id = str(uuid.uuid4())

        # 創建資料夾元數據記錄
        arangodb_client = get_arangodb_client()
        if arangodb_client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = arangodb_client.db.collection(FOLDER_COLLECTION_NAME)
        folder_doc = {
            "_key": task_id,
            "task_id": task_id,
            "folder_name": folder_name,
            "user_id": current_user.user_id,
            "parent_task_id": request_body.parent_task_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        collection.insert(folder_doc)

        logger.info(
            "Folder created successfully",
            task_id=task_id,
            folder_name=folder_name,
            parent_task_id=request_body.parent_task_id,
            user_id=current_user.user_id,
            is_root_level=request_body.parent_task_id is None,
        )

        return APIResponse.success(
            data={
                "task_id": task_id,
                "folder_name": folder_name,
                "user_id": current_user.user_id,
                "parent_task_id": request_body.parent_task_id,
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
    request: Request = None,
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
        collection.update(folder_doc)

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
        logger.error(
            "Failed to rename folder", folder_id=folder_id, error=str(e), exc_info=True
        )
        return APIResponse.error(
            message=f"重命名資料夾失敗: {str(e)}",
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
    request: Request = None,
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
                    logger.warning("刪除文件元數據失敗（繼續刪除文件）", file_id=file_id, error=str(e))

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
        logger.error(
            "Failed to delete folder", folder_id=folder_id, error=str(e), exc_info=True
        )
        return APIResponse.error(
            message=f"刪除資料夾失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/batch/download")
@audit_log(
    action=AuditAction.FILE_ACCESS,
    resource_type="file",
    get_resource_id=lambda body: body.get("data", {}).get("file_ids", [])[0]
    if body.get("data", {}).get("file_ids")
    else None,
)
async def batch_download_files(
    request_body: BatchDownloadRequest = Body(...),
    request: Request = None,
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
    request: Request = None,
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
            "upload_time": file_metadata.upload_time.isoformat()
            if hasattr(file_metadata.upload_time, "isoformat")
            else str(file_metadata.upload_time),
            "preview": file_content[:1000] if file_content else None,  # 前1000字符作為預覽
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

        storage = get_storage()

        # 檢查文件是否存在
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

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
        logger.error(
            "Failed to get file vectors", file_id=file_id, error=str(e), exc_info=True
        )
        return APIResponse.error(
            message=f"查詢向量資料失敗: {str(e)}",
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

        storage = get_storage()

        # 檢查文件是否存在
        if not storage.file_exists(file_id):
            return APIResponse.error(
                message="文件不存在",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從 Redis 讀取處理狀態獲取KG統計
        from database.redis import get_redis_client
        import json

        redis_client = get_redis_client()
        status_key = f"processing:status:{file_id}"
        status_data_str = redis_client.get(status_key)

        kg_stats = {
            "triples_count": 0,
            "entities_count": 0,
            "relations_count": 0,
            "status": "not_processed",
        }

        if status_data_str:
            status_data = json.loads(status_data_str)
            kg_extraction = status_data.get("kg_extraction", {})
            if kg_extraction.get("status") == "completed":
                kg_stats = {
                    "triples_count": kg_extraction.get("triples_count", 0),
                    "entities_count": kg_extraction.get("entities_count", 0),
                    "relations_count": kg_extraction.get("relations_count", 0),
                    "status": "completed",
                }

        # TODO: 實現從ArangoDB查詢文件相關的圖譜數據
        # 目前需要實現文件ID與三元組的關聯機制
        # 暫時返回統計信息和空列表

        logger.info(
            "Retrieved file graph data",
            file_id=file_id,
            kg_stats=kg_stats,
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={
                "file_id": file_id,
                "nodes": [],  # TODO: 實現節點查詢
                "edges": [],  # TODO: 實現邊查詢
                "triples": [],  # TODO: 實現三元組查詢
                "stats": kg_stats,
                "total": kg_stats.get("triples_count", 0),
                "limit": limit,
                "offset": offset,
            },
            message="圖譜資料查詢成功（部分功能待實現）",
        )
    except Exception as e:
        logger.error(
            "Failed to get file graph", file_id=file_id, error=str(e), exc_info=True
        )
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
    get_resource_id=lambda body: body.get("data", {}).get("file_ids", [])[0]
    if body.get("data", {}).get("file_ids")
    else None,
)
async def upload_from_library(
    request_body: LibraryUploadRequest = Body(...),
    request: Request = None,
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
                collection.update(file_doc)

                # 獲取更新後的文件元數據
                updated_doc = collection.get(file_id)
                if updated_doc is None:
                    failed_files.append({"file_id": file_id, "error": "文件更新失敗"})
                    continue

                updated_metadata = FileMetadata(**updated_doc)
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
    get_resource_id=lambda body: body.get("data", {}).get("file_ids", [])[0]
    if body.get("data", {}).get("file_ids")
    else None,
)
async def return_to_library(
    request_body: LibraryReturnRequest = Body(...),
    request: Request = None,
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
                collection.update(file_doc)

                # 獲取更新後的文件元數據
                updated_doc = collection.get(file_id)
                if updated_doc is None:
                    failed_files.append({"file_id": file_id, "error": "文件更新失敗"})
                    continue

                updated_metadata = FileMetadata(**updated_doc)
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
    request: Request = None,
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
                    file_doc.update(update_data)
                    collection.update(file_doc)
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
        library_files = [
            f for f in all_files if f.task_id in [None, LIBRARY_TASK_ID, ""]
        ]

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
