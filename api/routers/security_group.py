# 代碼功能說明: 安全群組管理路由
# 創建日期: 2026-01-17 19:41 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 11:15 UTC+8

"""安全群組管理路由 - 提供安全群組的 CRUD API"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Path, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.security_group import SecurityGroupCreate, SecurityGroupUpdate
from services.api.services.security_group_store_service import get_security_group_store_service
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


router = APIRouter(prefix="/admin/security-groups", tags=["Security Group"])


@router.get("", status_code=status.HTTP_200_OK)
async def list_security_groups(
    tenant_id: Optional[str] = Query(default=None, description="租戶 ID 過濾"),
    is_active: Optional[bool] = Query(default=None, description="是否啟用過濾"),
    limit: Optional[int] = Query(default=None, description="限制返回數量"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取安全群組列表

    Args:
        tenant_id: 租戶 ID 過濾（可選）
        is_active: 是否啟用過濾（可選）
        limit: 限制返回數量（可選）
        current_user: 當前認證用戶

    Returns:
        安全群組列表
    """
    try:
        service = get_security_group_store_service()
        groups = service.list_security_groups(tenant_id=tenant_id, is_active=is_active, limit=limit)

        groups_dicts = [group.model_dump(mode="json") for group in groups]

        return APIResponse.success(
            data={"groups": groups_dicts, "total": len(groups_dicts)},
            message="Security groups retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list security groups: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list security groups: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="security_group",
    get_resource_id=lambda body: body.get("data", {}).get("group_id"),
)
async def create_security_group(
    group: SecurityGroupCreate,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    創建安全群組

    Args:
        group: 安全群組創建數據
        current_user: 當前認證用戶

    Returns:
        創建的安全群組
    """
    try:
        service = get_security_group_store_service()
        created_group = service.create_security_group(group)

        logger.info(f"Security group created: group_id={created_group.group_id}")

        return APIResponse.success(
            data=created_group.model_dump(mode="json"),
            message="Security group created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error(f"Failed to create security group: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to create security group: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{group_id}", status_code=status.HTTP_200_OK)
async def get_security_group(
    group_id: str = Path(description="群組 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取安全群組詳情

    Args:
        group_id: 群組 ID
        current_user: 當前認證用戶

    Returns:
        安全群組詳情
    """
    try:
        service = get_security_group_store_service()
        group = service.get_security_group(group_id)

        if group is None:
            return APIResponse.error(
                message=f"Security group '{group_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(
            data=group.model_dump(mode="json"),
            message="Security group retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get security group: group_id={group_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get security group: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{group_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="security_group",
    get_resource_id=lambda group_id: group_id,
)
async def update_security_group(
    group_id: str = Path(description="群組 ID"),
    updates: SecurityGroupUpdate = None,  # type: ignore
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    更新安全群組

    Args:
        group_id: 群組 ID
        updates: 更新字段
        current_user: 當前認證用戶

    Returns:
        更新後的安全群組
    """
    try:
        service = get_security_group_store_service()

        if updates is None:
            return APIResponse.error(
                message="Updates are required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        updated_group = service.update_security_group(group_id, updates)

        if updated_group is None:
            return APIResponse.error(
                message=f"Security group '{group_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Security group updated: group_id={group_id}")

        return APIResponse.success(
            data=updated_group.model_dump(mode="json"),
            message="Security group updated successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to update security group: group_id={group_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to update security group: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{group_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="security_group",
    get_resource_id=lambda group_id: group_id,
)
async def delete_security_group(
    group_id: str = Path(description="群組 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    刪除安全群組

    Args:
        group_id: 群組 ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_security_group_store_service()
        success = service.delete_security_group(group_id)

        if not success:
            return APIResponse.error(
                message=f"Security group '{group_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"Security group deleted: group_id={group_id}")

        return APIResponse.success(
            data={"group_id": group_id},
            message="Security group deleted successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to delete security group: group_id={group_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to delete security group: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{group_id}/users/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="security_group",
    get_resource_id=lambda group_id: group_id,
)
async def add_user_to_group(
    group_id: str = Path(description="群組 ID"),
    user_id: str = Path(description="用戶 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    將用戶添加到安全群組

    Args:
        group_id: 群組 ID
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        更新後的安全群組
    """
    try:
        service = get_security_group_store_service()
        updated_group = service.add_user_to_group(group_id, user_id)

        if updated_group is None:
            return APIResponse.error(
                message=f"Security group '{group_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"User added to security group: group_id={group_id}, user_id={user_id}")

        return APIResponse.success(
            data=updated_group.model_dump(mode="json"),
            message="User added to security group successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to add user to security group: group_id={group_id}, user_id={user_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to add user to security group: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{group_id}/users/{user_id}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="security_group",
    get_resource_id=lambda group_id: group_id,
)
async def remove_user_from_group(
    group_id: str = Path(description="群組 ID"),
    user_id: str = Path(description="用戶 ID"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    從安全群組移除用戶

    Args:
        group_id: 群組 ID
        user_id: 用戶 ID
        current_user: 當前認證用戶

    Returns:
        更新後的安全群組
    """
    try:
        service = get_security_group_store_service()
        updated_group = service.remove_user_from_group(group_id, user_id)

        if updated_group is None:
            return APIResponse.error(
                message=f"Security group '{group_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        logger.info(f"User removed from security group: group_id={group_id}, user_id={user_id}")

        return APIResponse.success(
            data=updated_group.model_dump(mode="json"),
            message="User removed from security group successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to remove user from security group: group_id={group_id}, user_id={user_id}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to remove user from security group: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
