# 代碼功能說明: 文件上傳路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件上傳路由 - 提供文件上傳、驗證和存儲功能"""

import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, status
from fastapi.responses import JSONResponse
import structlog

from services.api.core.response import APIResponse
from services.api.utils.file_validator import (
    FileValidator,
    create_validator_from_config,
)
from services.api.storage.file_storage import (
    FileStorage,
    create_storage_from_config,
)
from services.api.services.file_metadata_service import FileMetadataService
from services.api.models.file_metadata import FileMetadataCreate
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["File Upload"])

# 全局驗證器、存儲和元數據服務實例（懶加載）
_validator: Optional[FileValidator] = None
_storage: Optional[FileStorage] = None
_metadata_service: Optional[FileMetadataService] = None


def get_validator() -> FileValidator:
    """獲取文件驗證器實例（單例模式）"""
    global _validator
    if _validator is None:
        config = get_config_section("file_upload", default={}) or {}
        _validator = create_validator_from_config(config)
    return _validator


def get_storage() -> FileStorage:
    """獲取文件存儲實例（單例模式）"""
    global _storage
    if _storage is None:
        config = get_config_section("file_upload", default={}) or {}
        _storage = create_storage_from_config(config)
    return _storage


def get_metadata_service() -> FileMetadataService:
    """獲取元數據服務實例（單例模式）"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service


@router.post("/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = None,
) -> JSONResponse:
    """
    上傳文件（支持多文件上傳）

    Args:
        files: 上傳的文件列表
        user_id: 用戶 ID（可選）

    Returns:
        上傳結果，包含文件 ID 和元數據
    """
    if not files:
        return APIResponse.error(
            message="未提供文件",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    validator = get_validator()
    storage = get_storage()

    results = []
    errors = []

    for file in files:
        try:
            # 讀取文件內容
            file_content = await file.read()

            # 驗證文件
            is_valid, error_msg = validator.validate_upload_file(
                file_content, file.filename
            )

            if not is_valid:
                errors.append(
                    {
                        "filename": file.filename,
                        "error": error_msg,
                    }
                )
                continue

            # 保存文件
            file_id, file_path = storage.save_file(file_content, file.filename)

            # 獲取文件類型
            file_type = validator.get_file_type(file.filename)

            # 創建元數據
            try:
                metadata_service = get_metadata_service()
                metadata_create = FileMetadataCreate(
                    file_id=file_id,
                    filename=file.filename,
                    file_type=file_type or "application/octet-stream",
                    file_size=len(file_content),
                    user_id=user_id,
                )
                metadata_service.create(metadata_create)
            except Exception as e:
                logger.warning(
                    "元數據創建失敗（文件已上傳）",
                    file_id=file_id,
                    error=str(e),
                )

            # 構建結果
            result = {
                "file_id": file_id,
                "filename": file.filename,
                "file_type": file_type,
                "file_size": len(file_content),
                "file_path": file_path,
            }

            results.append(result)

            logger.info(
                "文件上傳成功",
                file_id=file_id,
                filename=file.filename,
                file_size=len(file_content),
            )

        except Exception as e:
            logger.error(
                "文件上傳失敗",
                filename=file.filename,
                error=str(e),
            )
            errors.append(
                {
                    "filename": file.filename,
                    "error": f"上傳失敗: {str(e)}",
                }
            )

    # 構建響應
    response_data = {
        "uploaded": results,
        "errors": errors,
        "total": len(files),
        "success_count": len(results),
        "error_count": len(errors),
    }

    if errors and not results:
        # 所有文件都失敗
        return APIResponse.error(
            message="所有文件上傳失敗",
            details=response_data,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    elif errors:
        # 部分文件失敗
        return APIResponse.success(
            data=response_data,
            message=f"部分文件上傳成功（{len(results)}/{len(files)}）",
            status_code=status.HTTP_207_MULTI_STATUS,
        )
    else:
        # 所有文件成功
        return APIResponse.success(
            data=response_data,
            message=f"所有文件上傳成功（{len(results)} 個文件）",
        )


@router.get("/{file_id}")
async def get_file_info(file_id: str) -> JSONResponse:
    """
    獲取文件信息

    Args:
        file_id: 文件 ID

    Returns:
        文件信息
    """
    storage = get_storage()

    if not storage.file_exists(file_id):
        return APIResponse.error(
            message="文件不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    file_path = storage.get_file_path(file_id)
    if file_path:
        file_size = os.path.getsize(file_path)
        return APIResponse.success(
            data={
                "file_id": file_id,
                "file_path": file_path,
                "file_size": file_size,
            }
        )

    return APIResponse.error(
        message="無法獲取文件信息",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


@router.delete("/{file_id}")
async def delete_file(file_id: str) -> JSONResponse:
    """
    刪除文件

    Args:
        file_id: 文件 ID

    Returns:
        刪除結果
    """
    storage = get_storage()

    if not storage.file_exists(file_id):
        return APIResponse.error(
            message="文件不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    success = storage.delete_file(file_id)

    if success:
        return APIResponse.success(
            data={"file_id": file_id},
            message="文件刪除成功",
        )
    else:
        return APIResponse.error(
            message="文件刪除失敗",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
