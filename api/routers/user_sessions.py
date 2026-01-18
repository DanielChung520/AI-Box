# 代碼功能說明: 用戶會話管理路由
# 創建日期: 2026-01-17 18:07 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 11:15 UTC+8

"""用戶會話管理路由 - 提供用戶會話的查詢和管理 API"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.services.user_session_store_service import UserSessionStoreService
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = logging.getLogger(__name__)


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


router = APIRouter(prefix="/admin/sessions", tags=["User Session"])


def get_user_session_service() -> UserSessionStoreService:
    """獲取 UserSession Store Service 實例"""
    from services.api.services.user_session_store_service import get_user_session_store_service

    return get_user_session_store_service()


@router.get("", status_code=status.HTTP_200_OK)
async def list_all_sessions(
    include_inactive: bool = Query(default=False, description="是否包含未活躍的會話"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    offset: int = Query(default=0, description="偏移量（用於分頁）"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取所有活躍會話列表（僅 Super Admin）

    Args:
        include_inactive: 是否包含未活躍的會話
        limit: 限制返回數量
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        會話列表
    """
    try:
        service = get_user_session_service()

        # 僅 system_admin 可查看所有會話
        if not current_user.has_permission(Permission.ALL.value):
            return APIResponse.error(
                message="Access denied: Only system_admin can view all sessions",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        if include_inactive:
            # 如果包含未活躍會話，需要使用 AQL 查詢
            # 暫時只支持活躍會話列表
            return APIResponse.error(
                message="Listing inactive sessions is not supported yet",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        sessions, total = service.list_all_active_sessions(limit=limit, offset=offset)

        # 將會話轉換為字典（移除敏感信息如 access_token）
        session_dicts = []
        for session in sessions:
            session_dict = session.model_dump(mode="json")
            session_dict.pop("access_token", None)
            session_dict.pop("refresh_token", None)
            session_dicts.append(session_dict)

        return APIResponse.success(
            data={"sessions": session_dicts, "total": total, "limit": limit, "offset": offset},
            message="Sessions retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list all sessions: error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list sessions: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def list_user_sessions(
    user_id: str = Path(description="用戶 ID"),
    include_inactive: bool = Query(default=False, description="是否包含未活躍的會話"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    offset: int = Query(default=0, description="偏移量（用於分頁）"),
    current_user: User = Depends(require_system_admin),  # system_admin 或用戶本人可訪問
) -> JSONResponse:
    """
    獲取用戶會話列表

    Args:
        user_id: 用戶 ID
        include_inactive: 是否包含未活躍的會話
        limit: 限制返回數量
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        用戶會話列表
    """
    try:
        service = get_user_session_service()

        # 權限檢查：system_admin 可查看所有用戶，普通用戶只能查看自己的會話
        if not current_user.has_permission(Permission.ALL.value):
            if current_user.user_id != user_id:
                return APIResponse.error(
                    message="Access denied: You can only view your own sessions",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        sessions, total = service.list_user_sessions(
            user_id=user_id,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
        )

        # 將會話轉換為字典（移除敏感信息）
        session_dicts = []
        for session in sessions:
            session_dict = session.model_dump(mode="json")
            session_dict.pop("access_token", None)
            session_dict.pop("refresh_token", None)
            session_dicts.append(session_dict)

        return APIResponse.success(
            data={"sessions": session_dicts, "total": total, "limit": limit, "offset": offset},
            message="User sessions retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to list user sessions: user_id={user_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to list user sessions: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/users/{user_id}/sessions/{session_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="user_session",
    get_resource_id=lambda user_id, session_id: session_id,
)
async def terminate_session(
    user_id: str = Path(description="用戶 ID"),
    session_id: str = Path(description="會話 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    終止用戶會話（強制登出）

    Args:
        user_id: 用戶 ID
        session_id: 會話 ID
        current_user: 當前認證用戶

    Returns:
        終止結果
    """
    try:
        service = get_user_session_service()

        # 權限檢查：僅 system_admin 可強制終止會話
        if not current_user.has_permission(Permission.ALL.value):
            return APIResponse.error(
                message="Access denied: Only system_admin can terminate sessions",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 獲取會話信息
        session = service.get_session(session_id)
        if session is None:
            return APIResponse.error(
                message=f"Session '{session_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 驗證會話屬於指定用戶
        if session.user_id != user_id:
            return APIResponse.error(
                message=f"Session '{session_id}' does not belong to user '{user_id}'",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 終止會話
        success = service.terminate_session(session_id)

        if not success:
            return APIResponse.error(
                message=f"Failed to terminate session '{session_id}'",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"Session terminated: user_id={user_id}, session_id={session_id}")

        return APIResponse.success(
            data={"user_id": user_id, "session_id": session_id},
            message="Session terminated successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to terminate session: user_id={user_id}, session_id={session_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to terminate session: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="user_session",
    get_resource_id=lambda user_id: user_id,
)
async def terminate_all_user_sessions(
    user_id: str = Path(description="用戶 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    終止用戶的所有會話（強制全部登出）

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        終止結果
    """
    try:
        service = get_user_session_service()

        # 權限檢查：僅 system_admin 可強制終止所有會話
        if not current_user.has_permission(Permission.ALL.value):
            return APIResponse.error(
                message="Access denied: Only system_admin can terminate all user sessions",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 終止所有會話
        terminated_count = service.terminate_user_sessions(user_id)

        logger.info(f"All user sessions terminated: user_id={user_id}, count={terminated_count}")

        return APIResponse.success(
            data={"user_id": user_id, "terminated_count": terminated_count},
            message=f"All user sessions terminated successfully ({terminated_count} sessions)",
        )
    except Exception as e:
        logger.error(
            f"Failed to terminate all user sessions: user_id={user_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to terminate all user sessions: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{session_id}", status_code=status.HTTP_200_OK)
async def get_session(
    session_id: str = Path(description="會話 ID"),
    current_user: User = Depends(require_system_admin),  # system_admin 可訪問
) -> JSONResponse:
    """
    獲取會話詳情

    Args:
        session_id: 會話 ID
        current_user: 當前認證用戶

    Returns:
        會話詳情
    """
    try:
        service = get_user_session_service()

        # 權限檢查：system_admin 可查看所有會話
        if not current_user.has_permission(Permission.ALL.value):
            return APIResponse.error(
                message="Access denied: Only system_admin can view session details",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        session = service.get_session(session_id)

        if session is None:
            return APIResponse.error(
                message=f"Session '{session_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除敏感信息
        session_dict = session.model_dump(mode="json")
        session_dict.pop("access_token", None)
        session_dict.pop("refresh_token", None)

        return APIResponse.success(
            data=session_dict,
            message="Session retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get session: session_id={session_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to get session: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
