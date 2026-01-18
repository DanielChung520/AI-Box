# 代碼功能說明: RBAC 角色管理路由
# 創建日期: 2025-12-06 15:20 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:20 (UTC+8)

"""RBAC 角色管理路由 - 提供角色和權限管理API"""


import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.rbac import (
    RoleCreate,
    RoleModel,
    RoleUpdate,
    UserRoleAssign,
    UserRoleModel,
)
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


router = APIRouter(prefix="/rbac", tags=["RBAC"])


@router.post("/roles", status_code=status.HTTP_201_CREATED)
@audit_log(
    action=AuditAction.ROLE_CREATE,
    resource_type="role",
    get_resource_id=lambda body: body.get("data", {}).get("role_id"),
)
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(require_system_admin),  # 只有管理員可以創建角色
) -> JSONResponse:
    """
    創建角色

    Args:
        role_data: 角色數據
        current_user: 當前認證用戶

    Returns:
        創建的角色信息
    """
    try:
        # TODO: 實現角色創建邏輯（存儲到數據庫）
        # 當前返回模擬數據
        role = RoleModel(
            role_id=f"role_{len(role_data.name)}",
            name=role_data.name,
            description=role_data.description,
            created_at=None,  # type: ignore[call-arg]  # created_at 有默認值
            updated_at=None,  # type: ignore[call-arg]  # updated_at 有默認值
            permissions=role_data.permissions,
            is_system=role_data.is_system,
        )

        logger.info("角色創建成功", role_id=role.role_id, role_name=role.name)

        return APIResponse.success(
            data=role.model_dump(mode="json"),
            message="角色創建成功",
        )
    except Exception as e:
        logger.error("角色創建失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"角色創建失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/roles")
async def list_roles(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取角色列表

    Args:
        current_user: 當前認證用戶

    Returns:
        角色列表
    """
    try:
        # TODO: 實現角色列表查詢邏輯（從數據庫查詢）
        # 當前返回模擬數據
        roles = [
            RoleModel(
                role_id="admin",
                name="管理員",
                description="系統管理員角色",
                permissions=[Permission.ALL.value],
                is_system=True,
                created_at=None,  # type: ignore[call-arg]  # created_at 有默認值
                updated_at=None,  # type: ignore[call-arg]  # updated_at 有默認值
            ),
            RoleModel(
                role_id="user",
                name="普通用戶",
                description="普通用戶角色",
                created_at=None,  # type: ignore[call-arg]  # created_at 有默認值
                updated_at=None,  # type: ignore[call-arg]  # updated_at 有默認值
                permissions=[
                    Permission.FILE_UPLOAD.value,
                    Permission.FILE_READ_OWN.value,
                    Permission.FILE_DELETE_OWN.value,
                ],
                is_system=True,
            ),
        ]

        return APIResponse.success(
            data={"roles": [role.model_dump(mode="json") for role in roles]},
            message="角色列表查詢成功",
        )
    except Exception as e:
        logger.error("角色列表查詢失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"角色列表查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/roles/{role_id}")
async def get_role(
    role_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取角色詳情

    Args:
        role_id: 角色ID
        current_user: 當前認證用戶

    Returns:
        角色詳情
    """
    try:
        # TODO: 實現角色查詢邏輯（從數據庫查詢）
        # 當前返回模擬數據
        role = RoleModel(
            role_id=role_id,
            name="示例角色",
            description="示例角色描述",
            permissions=[],
            is_system=False,
            created_at=None,  # type: ignore[call-arg]  # created_at 有默認值
            updated_at=None,  # type: ignore[call-arg]  # updated_at 有默認值
        )

        return APIResponse.success(
            data=role.model_dump(mode="json"),
            message="角色查詢成功",
        )
    except Exception as e:
        logger.error("角色查詢失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"角色查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/roles/{role_id}")
@audit_log(
    action=AuditAction.ROLE_UPDATE,
    resource_type="role",
    get_resource_id=lambda role_id: role_id,
)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    current_user: User = Depends(require_system_admin),  # type: ignore[arg-type]  # require_permission 是異步函數，使用 partial 包裝
) -> JSONResponse:
    """
    更新角色

    Args:
        role_id: 角色ID
        role_data: 角色更新數據
        current_user: 當前認證用戶

    Returns:
        更新後的角色信息
    """
    try:
        # TODO: 實現角色更新邏輯（更新數據庫）
        # 當前返回模擬數據
        role = RoleModel(
            role_id=role_id,
            name=role_data.name or "更新後的角色",
            description=role_data.description,
            permissions=role_data.permissions or [],
            is_system=False,
            created_at=None,  # type: ignore[call-arg]  # created_at 有默認值
            updated_at=None,  # type: ignore[call-arg]  # updated_at 有默認值
        )

        logger.info("角色更新成功", role_id=role_id)

        return APIResponse.success(
            data=role.model_dump(mode="json"),
            message="角色更新成功",
        )
    except Exception as e:
        logger.error("角色更新失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"角色更新失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/roles/{role_id}")
@audit_log(
    action=AuditAction.ROLE_DELETE,
    resource_type="role",
    get_resource_id=lambda role_id: role_id,
)
async def delete_role(
    role_id: str,
    current_user: User = Depends(require_system_admin),  # type: ignore[arg-type]  # require_permission 是異步函數，使用 partial 包裝
) -> JSONResponse:
    """
    刪除角色

    Args:
        role_id: 角色ID
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        # TODO: 實現角色刪除邏輯（從數據庫刪除）
        # 檢查是否為系統角色，系統角色不能刪除

        logger.info("角色刪除成功", role_id=role_id)

        return APIResponse.success(
            data={"role_id": role_id},
            message="角色刪除成功",
        )
    except Exception as e:
        logger.error("角色刪除失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"角色刪除失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/users/{user_id}/roles")
@audit_log(
    action=AuditAction.USER_ROLE_ASSIGN,
    resource_type="user_role",
    get_resource_id=lambda user_id: user_id,
)
async def assign_user_role(
    user_id: str,
    role_data: UserRoleAssign,
    current_user: User = Depends(require_system_admin),  # type: ignore[arg-type]  # require_permission 是異步函數，使用 partial 包裝
) -> JSONResponse:
    """
    分配用戶角色

    Args:
        user_id: 用戶ID
        role_data: 角色分配數據
        current_user: 當前認證用戶

    Returns:
        分配結果
    """
    try:
        # TODO: 實現用戶角色分配邏輯（存儲到數據庫）
        user_role = UserRoleModel(
            user_id=user_id,
            role_id=role_data.role_id,
            assigned_by=current_user.user_id,
            expires_at=role_data.expires_at,
            assigned_at=None,  # type: ignore[call-arg]  # assigned_at 有默認值
        )

        logger.info("用戶角色分配成功", user_id=user_id, role_id=role_data.role_id)

        return APIResponse.success(
            data=user_role.model_dump(mode="json"),
            message="用戶角色分配成功",
        )
    except Exception as e:
        logger.error("用戶角色分配失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"用戶角色分配失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/users/{user_id}/roles/{role_id}")
@audit_log(
    action=AuditAction.USER_ROLE_REVOKE,
    resource_type="user_role",
    get_resource_id=lambda user_id: user_id,
)
async def revoke_user_role(
    user_id: str,
    role_id: str,
    current_user: User = Depends(require_system_admin),  # type: ignore[arg-type]  # require_permission 是異步函數，使用 partial 包裝
) -> JSONResponse:
    """
    撤銷用戶角色

    Args:
        user_id: 用戶ID
        role_id: 角色ID
        current_user: 當前認證用戶

    Returns:
        撤銷結果
    """
    try:
        # TODO: 實現用戶角色撤銷邏輯（從數據庫刪除）

        logger.info("用戶角色撤銷成功", user_id=user_id, role_id=role_id)

        return APIResponse.success(
            data={"user_id": user_id, "role_id": role_id},
            message="用戶角色撤銷成功",
        )
    except Exception as e:
        logger.error("用戶角色撤銷失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"用戶角色撤銷失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
