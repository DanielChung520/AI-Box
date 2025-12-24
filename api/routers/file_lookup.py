"""
代碼功能說明: 文件查找 API 路由
創建日期: 2025-12-20
創建人: Daniel Chung
最後修改日期: 2025-12-20
"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.services.file_metadata_service import FileMetadataService
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files", tags=["File Lookup"])


def get_file_metadata_service() -> FileMetadataService:
    return FileMetadataService()


@router.get("/lookup")
async def lookup_files(
    filename: Optional[str] = Query(None, description="文件名（支持部分匹配）"),
    task_id: Optional[str] = Query(None, description="任務 ID（用於限定搜索範圍）"),
    file_type: Optional[str] = Query(None, description="文件類型過濾"),
    limit: int = Query(10, ge=1, le=100, description="返回結果數量限制"),
    file_metadata_service: FileMetadataService = Depends(get_file_metadata_service),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    根據文件名查找文件

    支持按文件名（部分匹配）、任務 ID、文件類型進行查找。
    用於模組化文檔的虛擬合併預覽功能，根據文件名查找文件 ID。
    """
    logger.info(
        "Looking up files",
        filename=filename,
        task_id=task_id,
        file_type=file_type,
        user_id=current_user.user_id,
        tenant_id=tenant_id,
    )

    try:
        # 如果指定了文件名，使用文件查找邏輯
        if filename:
            # 使用 FileMetadataService 查找文件
            files = file_metadata_service.list(
                task_id=task_id,
                file_type=file_type,
                limit=limit * 10,  # 獲取更多文件以便過濾
            )

            # 過濾匹配文件名的文件
            matching_files = [f for f in files if filename.lower() in f.filename.lower()]

            # 限制返回數量
            result = matching_files[:limit]

            logger.info(
                "Files found",
                filename=filename,
                count=len(result),
            )

            return APIResponse.success(
                data=[f.model_dump(mode="json") for f in result],
                message=f"Found {len(result)} file(s) matching '{filename}'",
            )
        else:
            # 如果沒有指定文件名，返回任務下的所有文件
            files = file_metadata_service.list(
                task_id=task_id,
                file_type=file_type,
                limit=limit * 10,
            )

            result = files[:limit]

            return APIResponse.success(
                data=[f.model_dump(mode="json") for f in result],
                message=f"Found {len(result)} file(s)",
            )

    except Exception as e:
        logger.error("Failed to lookup files", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/lookup/exact")
async def lookup_file_exact(
    filename: str = Query(..., description="完整的文件名（精確匹配）"),
    task_id: Optional[str] = Query(None, description="任務 ID（用於限定搜索範圍）"),
    file_metadata_service: FileMetadataService = Depends(get_file_metadata_service),
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    根據文件名精確查找文件（返回第一個匹配的文件）

    用於模組化文檔的虛擬合併預覽功能，根據文件名精確查找文件 ID。
    """
    logger.info(
        "Looking up file by exact filename",
        filename=filename,
        task_id=task_id,
        user_id=current_user.user_id,
        tenant_id=tenant_id,
    )

    try:
        # 使用 FileMetadataService 查找文件
        files = file_metadata_service.list(task_id=task_id)

        # 精確匹配文件名
        matching_file = next((f for f in files if f.filename == filename), None)

        if matching_file:
            logger.info("File found", filename=filename, file_id=matching_file.file_id)
            return APIResponse.success(
                data=matching_file.model_dump(mode="json"),
                message="File found",
            )
        else:
            logger.info("File not found", filename=filename)
            return APIResponse.error(
                message=f"File not found: {filename}",
                status_code=status.HTTP_404_NOT_FOUND,
            )

    except Exception as e:
        logger.error("Failed to lookup file", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
