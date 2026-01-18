# 代碼功能說明: 審計日誌路由
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""審計日誌路由 - 提供審計日誌查詢和導出功能。"""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction, AuditLogResponse
from services.api.services.audit_log_service import get_audit_log_service
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)


# 創建需要系統管理員權限的依賴函數
async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    """檢查用戶是否擁有系統管理員權限的依賴函數（修改時間：2026-01-18）"""
    from fastapi import HTTPException

    from system.security.config import get_security_settings

    settings = get_security_settings()

    # 開發模式下自動通過權限檢查
    if settings.should_bypass_auth:
        return user

    # 生產模式下進行真實權限檢查
    if not settings.rbac.enabled:
        # 如果 RBAC 未啟用，則所有已認證用戶都可以訪問
        return user

    if not user.has_permission(Permission.ALL.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: system_admin",
        )

    return user


router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse])
async def query_audit_logs(
    user_id: Optional[str] = Query(None, description="用戶ID"),
    action: Optional[AuditAction] = Query(None, description="操作類型"),
    resource_type: Optional[str] = Query(None, description="資源類型"),
    resource_id: Optional[str] = Query(None, description="資源ID"),
    start_date: Optional[str] = Query(None, description="開始時間（ISO 8601格式）"),
    end_date: Optional[str] = Query(None, description="結束時間（ISO 8601格式）"),
    limit: int = Query(100, ge=1, le=1000, description="返回記錄數限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(require_system_admin),
) -> JSONResponse:
    """查詢審計日誌。

    需要管理員權限。

    Args:
        user_id: 用戶ID（可選）
        action: 操作類型（可選）
        resource_type: 資源類型（可選）
        resource_id: 資源ID（可選）
        start_date: 開始時間（ISO 8601格式，可選）
        end_date: 結束時間（ISO 8601格式，可選）
        limit: 返回記錄數限制
        offset: 偏移量
        current_user: 當前認證用戶（需要管理員權限）

    Returns:
        審計日誌列表和總數
    """
    service = get_audit_log_service()

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
    logs, total = service.query_logs(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_datetime,
        end_date=end_datetime,
        limit=limit,
        offset=offset,
    )

    return APIResponse.success(
        data={
            "logs": [
                AuditLogResponse(
                    user_id=log.user_id,
                    action=log.action,
                    resource_type=log.resource_type,
                    resource_id=log.resource_id,
                    timestamp=log.timestamp,
                    ip_address=log.ip_address,
                    user_agent=log.user_agent,
                    details=log.details,
                )
                for log in logs
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        },
        message="Audit logs retrieved successfully",
    )


@router.get("/export")
async def export_audit_logs(
    format: str = Query("json", regex="^(json|csv)$", description="導出格式（json 或 csv）"),
    user_id: Optional[str] = Query(None, description="用戶ID"),
    action: Optional[AuditAction] = Query(None, description="操作類型"),
    start_date: Optional[str] = Query(None, description="開始時間（ISO 8601格式）"),
    end_date: Optional[str] = Query(None, description="結束時間（ISO 8601格式）"),
    limit: int = Query(10000, ge=1, le=100000, description="導出記錄數限制"),
    current_user: User = Depends(require_system_admin),
) -> Response:
    """導出審計日誌。

    需要管理員權限。

    Args:
        format: 導出格式（"json" 或 "csv"）
        user_id: 用戶ID（可選）
        action: 操作類型（可選）
        start_date: 開始時間（ISO 8601格式，可選）
        end_date: 結束時間（ISO 8601格式，可選）
        limit: 導出記錄數限制
        current_user: 當前認證用戶（需要管理員權限）

    Returns:
        導出的審計日誌文件
    """
    service = get_audit_log_service()

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

    # 導出日誌
    exported_data = service.export_logs(
        format=format,
        user_id=user_id,
        action=action,
        start_date=start_datetime,
        end_date=end_datetime,
        limit=limit,
    )

    # 設置響應頭
    content_type = "application/json" if format == "json" else "text/csv"
    filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.{format}"

    return Response(
        content=exported_data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
