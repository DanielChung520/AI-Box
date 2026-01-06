# 代碼功能說明: 文件訪問審計路由 (WBS-4.4.3)
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""文件訪問審計路由 - 提供文件訪問日誌查詢和統計功能"""

from datetime import datetime
from functools import partial
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.services.file_audit_service import get_file_audit_service
from system.security.dependencies import require_permission
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/files/audit", tags=["File Audit"])


@router.get("/logs")
async def get_file_access_logs(
    file_id: Optional[str] = Query(None, description="文件 ID"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    granted: Optional[bool] = Query(None, description="是否授權（true=授權, false=拒絕）"),
    start_date: Optional[str] = Query(None, description="開始時間（ISO 8601格式）"),
    end_date: Optional[str] = Query(None, description="結束時間（ISO 8601格式）"),
    limit: int = Query(100, ge=1, le=1000, description="返回記錄數限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(partial(require_permission, Permission.ALL.value)),
) -> JSONResponse:
    """查詢文件訪問日誌 (WBS-4.4.3)

    需要管理員權限。

    Args:
        file_id: 文件 ID（可選，如果提供則查詢該文件的訪問日誌）
        user_id: 用戶 ID（可選，如果提供則過濾特定用戶的訪問）
        granted: 是否授權（可選，true 表示授權，false 表示拒絕）
        start_date: 開始時間（ISO 8601格式，可選）
        end_date: 結束時間（ISO 8601格式，可選）
        limit: 返回記錄數限制
        offset: 偏移量
        current_user: 當前認證用戶（需要管理員權限）

    Returns:
        文件訪問日誌列表和總數
    """
    if not file_id and not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either file_id or user_id must be provided",
        )

    service = get_file_audit_service()

    # 解析日期
    start_datetime: Optional[datetime] = None
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {e}",
            )

    end_datetime: Optional[datetime] = None
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format: {e}",
            )

    # 查詢日誌
    if file_id:
        logs, total = service.get_file_access_logs(
            file_id=file_id,
            user_id=user_id,
            granted=granted,
            start_date=start_datetime,
            end_date=end_datetime,
            limit=limit,
            offset=offset,
        )
    else:
        # 如果只提供了 user_id，使用 get_user_access_logs
        logs, total = service.get_user_access_logs(
            user_id=user_id or "",
            file_id=None,
            granted=granted,
            start_date=start_datetime,
            end_date=end_datetime,
            limit=limit,
            offset=offset,
        )

    return APIResponse.success(
        data={
            "logs": logs,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        message="File access logs retrieved successfully",
    )


@router.get("/statistics")
async def get_access_statistics(
    file_id: Optional[str] = Query(None, description="文件 ID"),
    user_id: Optional[str] = Query(None, description="用戶 ID"),
    start_date: Optional[str] = Query(None, description="開始時間（ISO 8601格式）"),
    end_date: Optional[str] = Query(None, description="結束時間（ISO 8601格式）"),
    current_user: User = Depends(partial(require_permission, Permission.ALL.value)),
) -> JSONResponse:
    """獲取文件訪問統計信息 (WBS-4.4.3)

    需要管理員權限。

    Args:
        file_id: 文件 ID（可選，如果提供則統計該文件的訪問）
        user_id: 用戶 ID（可選，如果提供則統計該用戶的訪問）
        start_date: 開始時間（ISO 8601格式，可選）
        end_date: 結束時間（ISO 8601格式，可選）
        current_user: 當前認證用戶（需要管理員權限）

    Returns:
        訪問統計信息
    """
    service = get_file_audit_service()

    # 解析日期
    start_datetime: Optional[datetime] = None
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid start_date format: {e}",
            )

    end_datetime: Optional[datetime] = None
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid end_date format: {e}",
            )

    # 獲取統計信息
    statistics = service.get_access_statistics(
        file_id=file_id,
        user_id=user_id,
        start_date=start_datetime,
        end_date=end_datetime,
    )

    return APIResponse.success(
        data=statistics,
        message="Access statistics retrieved successfully",
    )
