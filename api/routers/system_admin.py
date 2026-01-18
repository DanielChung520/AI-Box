# 代碼功能說明: 系統用戶管理路由
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 11:15 UTC+8

"""系統用戶管理路由 - 提供 Super Admin 用戶的 CRUD API"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.system_user import PasswordResetRequest, SystemUserCreate, SystemUserUpdate
from services.api.services.system_user_store_service import SystemUserStoreService
from system.security.audit_decorator import audit_log
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


router = APIRouter(prefix="/admin/system-users", tags=["System Admin"])


def get_system_user_service() -> SystemUserStoreService:
    """獲取 SystemUser Store Service 實例"""
    return SystemUserStoreService()


@router.get("", status_code=status.HTTP_200_OK)
async def list_system_users(
    include_inactive: bool = Query(default=False, description="是否包含未啟用的用戶"),
    limit: Optional[int] = Query(default=None, description="限制返回數量"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取系統用戶列表

    Args:
        include_inactive: 是否包含未啟用的用戶
        limit: 限制返回數量
        current_user: 當前認證用戶

    Returns:
        系統用戶列表
    """
    try:
        service = get_system_user_service()
        users = service.list_system_users(include_inactive=include_inactive, limit=limit)

        # 移除密碼哈希（安全考慮）
        user_dicts = []
        for user in users:
            user_dict = user.model_dump(mode="json")
            user_dict.pop("password_hash", None)  # 移除密碼哈希
            user_dicts.append(user_dict)

        return APIResponse.success(
            data={"users": user_dicts, "total": len(user_dicts)},
            message="System users retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list system users: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list system users: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_system_user(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取系統用戶詳情

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        系統用戶詳情
    """
    try:
        service = get_system_user_service()
        user = service.get_system_user(user_id)

        if user is None:
            return APIResponse.error(
                message=f"System user '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        return APIResponse.success(
            data=user_dict,
            message="System user retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to get system user: user_id={user_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to get system user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
@audit_log(
    action=AuditAction.USER_CREATE,
    resource_type="system_user",
    get_resource_id=lambda body: body.get("data", {}).get("user_id"),
)
async def create_system_user(
    user_data: SystemUserCreate,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    創建新的系統用戶

    Args:
        user_data: 用戶創建數據
        current_user: 當前認證用戶

    Returns:
        創建的用戶信息
    """
    try:
        service = get_system_user_service()
        created_user = service.create_system_user(user_data)

        # 移除密碼哈希（安全考慮）
        user_dict = created_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(f"System user created: user_id={created_user.user_id}")

        return APIResponse.success(
            data=user_dict,
            message="System user created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except ValueError as e:
        logger.warning(f"Failed to create system user: {str(e)}")
        return APIResponse.error(
            message=f"Failed to create system user: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Failed to create system user: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to create system user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_UPDATE,
    resource_type="system_user",
    get_resource_id=lambda user_id: user_id,
)
async def update_system_user(
    user_id: str,
    user_data: SystemUserUpdate,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    更新系統用戶信息

    Args:
        user_id: 用戶 ID
        user_data: 用戶更新數據
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        service = get_system_user_service()
        updated_user = service.update_system_user(user_id, user_data)

        if updated_user is None:
            return APIResponse.error(
                message=f"System user '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(f"System user updated: user_id={user_id}")

        return APIResponse.success(
            data=user_dict,
            message="System user updated successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to update system user: user_id={user_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to update system user: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to update system user: user_id={user_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to update system user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_DELETE,
    resource_type="system_user",
    get_resource_id=lambda user_id: user_id,
)
async def delete_system_user(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    刪除系統用戶（軟刪除）

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_system_user_service()
        success = service.delete_system_user(user_id)

        if not success:
            return APIResponse.error(
                message=f"System user '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"System user deleted: user_id={user_id}")

        return APIResponse.success(
            data={"user_id": user_id},
            message="System user deleted successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to delete system user: user_id={user_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to delete system user: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to delete system user: user_id={user_id}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to delete system user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_UPDATE,
    resource_type="system_user",
    get_resource_id=lambda user_id: user_id,
)
async def reset_password(
    user_id: str,
    request: PasswordResetRequest,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    重置系統用戶密碼

    Args:
        user_id: 用戶 ID
        request: 密碼重置請求
        current_user: 當前認證用戶

    Returns:
        重置結果
    """
    try:
        service = get_system_user_service()
        success = service.reset_password(user_id, request.new_password)

        if not success:
            return APIResponse.error(
                message=f"System user '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Password reset for system user: user_id={user_id}")

        return APIResponse.success(
            data={"user_id": user_id},
            message="Password reset successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to reset password for system user: user_id={user_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to reset password: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{user_id}/toggle-active", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_UPDATE,
    resource_type="system_user",
    get_resource_id=lambda user_id: user_id,
)
async def toggle_active(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    切換系統用戶啟用狀態

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        service = get_system_user_service()
        updated_user = service.toggle_active(user_id)

        if updated_user is None:
            return APIResponse.error(
                message=f"System user '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(
            f"System user active status toggled: user_id={user_id}, is_active={updated_user.is_active}"
        )

        return APIResponse.success(
            data=user_dict,
            message="System user active status toggled successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to toggle active status: user_id={user_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to toggle active status: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            f"Failed to toggle active status: user_id={user_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to toggle active status: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
