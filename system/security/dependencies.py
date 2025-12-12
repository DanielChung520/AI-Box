# 代碼功能說明: FastAPI 依賴注入函數
# 創建日期: 2025-11-26 01:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 09:21:13 UTC+8

"""FastAPI 依賴注入函數 - 提供認證和授權依賴。

這些函數可以在路由中使用 FastAPI 的 Depends() 機制來進行認證和授權檢查。
"""

from fastapi import Request, HTTPException, status, Depends

from system.security.config import get_security_settings
from system.security.models import User
from system.security.auth import authenticate_request


async def get_current_user(request: Request) -> User:
    """獲取當前認證用戶的依賴函數。

    此函數可以在路由中使用，例如：
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.user_id}

    在開發模式下（SECURITY_ENABLED=false 或 SECURITY_MODE=development），
    如果提供了有效的 JWT token，會從 token 中解析用戶信息；否則返回開發用戶。

    Args:
        request: FastAPI Request 對象

    Returns:
        User 對象

    Raises:
        HTTPException: 如果認證失敗（僅在生產模式下）

    TODO (WBS 1.6.1, WBS 1.6.2): 完善認證邏輯
      - 當 security.enabled=true 且 security.mode=production 時，需要真實認證
      - 實現 JWT Token 和 API Key 的完整驗證流程
    """
    import structlog

    logger = structlog.get_logger(__name__)

    settings = get_security_settings()

    # 修改時間：2025-01-27 - 修復開發模式下從 JWT token 解析用戶信息
    # 優先嘗試從 JWT token 解析用戶信息（即使在開發模式下）
    user = await authenticate_request(request)

    # 修改時間：2025-01-27 - 添加日誌記錄以便調試
    if user:
        # 如果成功解析到用戶信息，使用該用戶
        logger.debug(
            "User authenticated from token",
            user_id=user.user_id,
            username=user.username,
            has_token=True,
        )
        return user

    # 修改時間：2025-01-27 - 移除 dev_user fallback，正式測試環境要求真實認證
    # 檢查是否有 token
    from system.security.auth import extract_token_from_request

    token = await extract_token_from_request(request)
    if token:
        logger.warning(
            "Token provided but authentication failed",
            token_length=len(token),
            should_bypass_auth=settings.should_bypass_auth,
        )
    else:
        logger.debug(
            "No token provided", should_bypass_auth=settings.should_bypass_auth
        )

    # 修改時間：2025-01-27 - 正式測試：移除 dev_user fallback
    # 只有在 SECURITY_ENABLED=false 時才允許繞過認證
    if settings.should_bypass_auth:
        # 只有在安全功能完全禁用時才允許繞過
        logger.warning(
            "Security is disabled, allowing unauthenticated access",
            should_bypass_auth=True,
        )
        # 返回一個臨時用戶（用於測試，但不會使用 dev_user）
        # 注意：這應該只在安全功能完全禁用時使用
        return User(
            user_id="unauthenticated",
            username="unauthenticated",
            email=None,
            roles=[],
            permissions=[],
            is_active=True,
            metadata={"bypass_auth": True},
        )

    # 正式測試環境：要求真實認證，認證失敗則拋出異常
    user = await authenticate_request(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid JWT token or API key.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user


async def require_permission(
    permission: str,
    user: User = Depends(get_current_user),
) -> User:
    """檢查用戶是否擁有指定權限的依賴函數。

    此函數可以在路由中使用，例如：
        @router.delete("/tasks/{task_id}")
        async def delete_task(
            task_id: str,
            user: User = Depends(require_permission(Permission.TASK_DELETE.value))
        ):
            # 用戶必須擁有 TASK_DELETE 權限才能執行此操作
            ...

    在開發模式下，此檢查會自動通過。

    Args:
        permission: 需要的權限字符串
        user: 當前用戶（通過 get_current_user 依賴注入）

    Returns:
        User 對象（如果權限檢查通過）

    Raises:
        HTTPException: 如果用戶沒有所需權限

    TODO (WBS 1.6.3): 實現完整的 RBAC 權限系統
      - 實現角色和權限策略文件解析
      - 支持複雜的權限組合（AND、OR、NOT）
      - 實現權限審計日誌
      - 支持動態權限分配
    """
    settings = get_security_settings()

    # 開發模式下自動通過權限檢查
    if settings.should_bypass_auth:
        return user

    # 生產模式下進行真實權限檢查
    if not settings.rbac.enabled:
        # 如果 RBAC 未啟用，則所有已認證用戶都可以訪問
        return user

    if not user.has_permission(permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required: {permission}",
        )

    return user


def require_any_permission(*permissions: str):
    """創建一個需要任意一個權限的依賴函數。

    例如：
        @router.get("/data")
        async def get_data(
            user: User = Depends(require_any_permission("read:data", "admin"))
        ):
            ...

    Args:
        *permissions: 權限列表，用戶只需擁有其中一個即可

    Returns:
        依賴函數

    TODO (WBS 1.6.3): 在完整 RBAC 實施時，完善此函數的實現
    """

    async def check_permissions(user: User = Depends(get_current_user)) -> User:
        settings = get_security_settings()
        if settings.should_bypass_auth:
            return user

        if not settings.rbac.enabled:
            return user

        if not user.has_any_permission(*permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {', '.join(permissions)}",
            )

        return user

    return check_permissions


def require_all_permissions(*permissions: str):
    """創建一個需要所有權限的依賴函數。

    例如：
        @router.post("/admin/action")
        async def admin_action(
            user: User = Depends(require_all_permissions("admin", "write:data"))
        ):
            ...

    Args:
        *permissions: 權限列表，用戶必須擁有所有權限

    Returns:
        依賴函數

    TODO (WBS 1.6.3): 在完整 RBAC 實施時，完善此函數的實現
    """

    async def check_permissions(user: User = Depends(get_current_user)) -> User:
        settings = get_security_settings()
        if settings.should_bypass_auth:
            return user

        if not settings.rbac.enabled:
            return user

        if not user.has_all_permissions(*permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {', '.join(permissions)}",
            )

        return user

    return check_permissions
