# 代碼功能說明: 用戶賬號管理路由
# 創建日期: 2026-01-17 17:33 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 10:35 UTC+8

"""用戶賬號管理路由 - 提供用戶賬號的 CRUD API"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.user_account import (
    PasswordResetRequest,
    UserAccountCreate,
    UserAccountUpdate,
    UserRoleAssignment,
)
from services.api.services.user_account_store_service import UserAccountStoreService
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/users", tags=["User Account"])


def get_user_account_service() -> UserAccountStoreService:
    """獲取 UserAccount Store Service 實例"""
    from services.api.services.user_account_store_service import get_user_account_store_service

    return get_user_account_store_service()


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


@router.get("", status_code=status.HTTP_200_OK)
async def list_users(
    tenant_id: Optional[str] = Query(default=None, description="租戶 ID（可選）"),
    include_inactive: bool = Query(default=False, description="是否包含未啟用的用戶"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    offset: int = Query(default=0, description="偏移量（用於分頁）"),
    search: Optional[str] = Query(default=None, description="搜索關鍵字（用戶名或郵箱）"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取用戶列表（支持分頁、搜索、過濾）

    Args:
        tenant_id: 租戶 ID（可選）
        include_inactive: 是否包含未啟用的用戶
        limit: 限制返回數量
        offset: 偏移量
        search: 搜索關鍵字
        current_user: 當前認證用戶

    Returns:
        用戶列表
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能查看本租戶用戶
        if current_user.has_role("tenant_admin") and not current_user.has_permission(
            Permission.ALL.value
        ):
            # 從 current_user 的 metadata 中獲取 tenant_id
            user_tenant_id = current_user.metadata.get("tenant_id")
            if user_tenant_id:
                tenant_id = user_tenant_id

        users, total = service.list_user_accounts(
            tenant_id=tenant_id,
            include_inactive=include_inactive,
            limit=limit,
            offset=offset,
            search=search,
        )

        # 移除密碼哈希（安全考慮）
        user_dicts = []
        for user in users:
            user_dict = user.model_dump(mode="json")
            user_dict.pop("password_hash", None)
            user_dicts.append(user_dict)

        return APIResponse.success(
            data={"users": user_dicts, "total": total, "limit": limit, "offset": offset},
            message="Users retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list users: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list users: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取用戶詳情

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        用戶詳情
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能查看本租戶用戶
        user = service.get_user_account(user_id)
        if user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if current_user.has_role("tenant_admin") and not current_user.has_permission(
            Permission.ALL.value
        ):
            user_tenant_id = current_user.metadata.get("tenant_id")
            if user.tenant_id != user_tenant_id:
                return APIResponse.error(
                    message="Access denied: You can only view users in your tenant",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        # 移除密碼哈希（安全考慮）
        user_dict = user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        return APIResponse.success(
            data=user_dict,
            message="User retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to get user: user_id={user_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to get user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
@audit_log(
    action=AuditAction.USER_CREATE,
    resource_type="user_account",
    get_resource_id=lambda body: body.get("data", {}).get("user_id"),
)
async def create_user(
    user_data: UserAccountCreate,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    創建新用戶

    Args:
        user_data: 用戶創建數據
        current_user: 當前認證用戶

    Returns:
        創建的用戶信息
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能創建本租戶用戶
        if current_user.has_role("tenant_admin") and not current_user.has_permission(
            Permission.ALL.value
        ):
            user_tenant_id = current_user.metadata.get("tenant_id")
            if user_tenant_id:
                user_data.tenant_id = user_tenant_id

        created_user = service.create_user_account(user_data)

        # 移除密碼哈希（安全考慮）
        user_dict = created_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(f"User account created: user_id={created_user.user_id}")

        return APIResponse.success(
            data=user_dict,
            message="User created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except ValueError as e:
        logger.warning(f"Failed to create user: {str(e)}")
        return APIResponse.error(
            message=f"Failed to create user: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to create user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_UPDATE,
    resource_type="user_account",
    get_resource_id=lambda user_id: user_id,
)
async def update_user(
    user_id: str,
    user_data: UserAccountUpdate,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    更新用戶信息

    Args:
        user_id: 用戶 ID
        user_data: 用戶更新數據
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能更新本租戶用戶
        existing_user = service.get_user_account(user_id)
        if existing_user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if current_user.has_role("tenant_admin") and not current_user.has_permission(
            Permission.ALL.value
        ):
            user_tenant_id = current_user.metadata.get("tenant_id")
            if existing_user.tenant_id != user_tenant_id:
                return APIResponse.error(
                    message="Access denied: You can only update users in your tenant",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        updated_user = service.update_user_account(user_id, user_data)

        if updated_user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(f"User account updated: user_id={user_id}")

        return APIResponse.success(
            data=user_dict,
            message="User updated successfully",
        )
    except ValueError as e:
        logger.warning(f"Failed to update user: user_id={user_id}, error={str(e)}")
        return APIResponse.error(
            message=f"Failed to update user: {str(e)}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Failed to update user: user_id={user_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to update user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_DELETE,
    resource_type="user_account",
    get_resource_id=lambda user_id: user_id,
)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    刪除用戶（軟刪除）

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能刪除本租戶用戶
        existing_user = service.get_user_account(user_id)
        if existing_user:
            if current_user.has_role("tenant_admin") and not current_user.has_permission(
                Permission.ALL.value
            ):
                user_tenant_id = current_user.metadata.get("tenant_id")
                if existing_user.tenant_id != user_tenant_id:
                    return APIResponse.error(
                        message="Access denied: You can only delete users in your tenant",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        success = service.delete_user_account(user_id)

        if not success:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"User account deleted: user_id={user_id}")

        return APIResponse.success(
            data={"user_id": user_id},
            message="User deleted successfully",
        )
    except Exception as e:
        logger.error(f"Failed to delete user: user_id={user_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to delete user: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{user_id}/reset-password", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_UPDATE,
    resource_type="user_account",
    get_resource_id=lambda user_id: user_id,
)
async def reset_password(
    user_id: str,
    request: PasswordResetRequest,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    重置用戶密碼

    Args:
        user_id: 用戶 ID
        request: 密碼重置請求
        current_user: 當前認證用戶

    Returns:
        重置結果
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能重置本租戶用戶密碼
        existing_user = service.get_user_account(user_id)
        if existing_user:
            if current_user.has_role("tenant_admin") and not current_user.has_permission(
                Permission.ALL.value
            ):
                user_tenant_id = current_user.metadata.get("tenant_id")
                if existing_user.tenant_id != user_tenant_id:
                    return APIResponse.error(
                        message="Access denied: You can only reset passwords for users in your tenant",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        success = service.reset_password(user_id, request.new_password)

        if not success:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Password reset for user account: user_id={user_id}")

        return APIResponse.success(
            data={"user_id": user_id},
            message="Password reset successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to reset password for user: user_id={user_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to reset password: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{user_id}/toggle-active", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_UPDATE,
    resource_type="user_account",
    get_resource_id=lambda user_id: user_id,
)
async def toggle_active(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    切換用戶啟用狀態

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能切換本租戶用戶狀態
        existing_user = service.get_user_account(user_id)
        if existing_user:
            if current_user.has_role("tenant_admin") and not current_user.has_permission(
                Permission.ALL.value
            ):
                user_tenant_id = current_user.metadata.get("tenant_id")
                if existing_user.tenant_id != user_tenant_id:
                    return APIResponse.error(
                        message="Access denied: You can only toggle active status for users in your tenant",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        updated_user = service.toggle_active(user_id)

        if updated_user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(
            f"User account active status toggled: user_id={user_id}, is_active={updated_user.is_active}"
        )

        return APIResponse.success(
            data=user_dict,
            message="User active status toggled successfully",
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


@router.get("/{user_id}/roles", status_code=status.HTTP_200_OK)
async def get_user_roles(
    user_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取用戶角色列表

    Args:
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        用戶角色列表
    """
    try:
        service = get_user_account_service()
        user = service.get_user_account(user_id)

        if user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 權限檢查：tenant_admin 只能查看本租戶用戶角色
        if current_user.has_role("tenant_admin") and not current_user.has_permission(
            Permission.ALL.value
        ):
            user_tenant_id = current_user.metadata.get("tenant_id")
            if user.tenant_id != user_tenant_id:
                return APIResponse.error(
                    message="Access denied: You can only view roles for users in your tenant",
                    status_code=status.HTTP_403_FORBIDDEN,
                )

        return APIResponse.success(
            data={"user_id": user_id, "roles": user.roles},
            message="User roles retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to get user roles: user_id={user_id}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to get user roles: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{user_id}/roles", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_ROLE_ASSIGN,
    resource_type="user_account",
    get_resource_id=lambda user_id: user_id,
)
async def assign_role(
    user_id: str,
    request: UserRoleAssignment,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    分配角色給用戶

    Args:
        user_id: 用戶 ID
        request: 角色分配請求
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能分配角色給本租戶用戶
        existing_user = service.get_user_account(user_id)
        if existing_user:
            if current_user.has_role("tenant_admin") and not current_user.has_permission(
                Permission.ALL.value
            ):
                user_tenant_id = current_user.metadata.get("tenant_id")
                if existing_user.tenant_id != user_tenant_id:
                    return APIResponse.error(
                        message="Access denied: You can only assign roles to users in your tenant",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        updated_user = service.assign_role(user_id, request.role_id)

        if updated_user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(f"Role assigned to user: user_id={user_id}, role_id={request.role_id}")

        return APIResponse.success(
            data=user_dict,
            message="Role assigned successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to assign role: user_id={user_id}, role_id={request.role_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to assign role: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.USER_ROLE_REVOKE,
    resource_type="user_account",
    get_resource_id=lambda user_id: user_id,
)
async def revoke_role(
    user_id: str,
    role_id: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    撤銷用戶角色

    Args:
        user_id: 用戶 ID
        role_id: 角色 ID
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        service = get_user_account_service()

        # 權限檢查：tenant_admin 只能撤銷本租戶用戶角色
        existing_user = service.get_user_account(user_id)
        if existing_user:
            if current_user.has_role("tenant_admin") and not current_user.has_permission(
                Permission.ALL.value
            ):
                user_tenant_id = current_user.metadata.get("tenant_id")
                if existing_user.tenant_id != user_tenant_id:
                    return APIResponse.error(
                        message="Access denied: You can only revoke roles from users in your tenant",
                        status_code=status.HTTP_403_FORBIDDEN,
                    )

        updated_user = service.revoke_role(user_id, role_id)

        if updated_user is None:
            return APIResponse.error(
                message=f"User '{user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(f"Role revoked from user: user_id={user_id}, role_id={role_id}")

        return APIResponse.success(
            data=user_dict,
            message="Role revoked successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to revoke role: user_id={user_id}, role_id={role_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to revoke role: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
