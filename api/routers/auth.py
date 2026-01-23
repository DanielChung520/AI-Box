# 代碼功能說明: 認證路由
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 23:15 UTC+8

"""認證路由 - 提供登錄、Token刷新、登出等功能。"""

import os
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.jwt_service import get_jwt_service
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """登錄請求模型"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """登錄響應模型"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """刷新 Token 請求模型"""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """刷新 Token 響應模型"""

    access_token: str
    token_type: str = "bearer"


def _authenticate_user(username: str, password: str) -> Optional[User]:
    """驗證用戶憑證。

    這是一個簡單的實現，實際應用中應該：
    - 從數據庫查詢用戶
    - 驗證密碼哈希
    - 檢查用戶狀態（是否啟用、是否鎖定等）

    Args:
        username: 用戶名（可以是 email）
        password: 密碼

    Returns:
        User 對象，如果驗證失敗則返回 None
    """
    # 修改時間：2026-01-17 17:13 UTC+8 - 從數據庫查詢 systemAdmin 用戶並驗證密碼
    # 修改時間：2025-12-08 09:15:21 UTC+8 - 修復開發模式下的用戶認證，使用實際用戶 ID
    # 開發模式下，接受任何用戶名/密碼組合，但使用實際的用戶名/email 作為 user_id
    # TODO: 實現真實的用戶認證邏輯（普通用戶）
    # 這裡暫時實現一個簡單的驗證（僅用於演示）
    # 在生產環境中，應該從數據庫查詢用戶並驗證密碼

    # 修改時間：2026-01-17 17:13 UTC+8 - 從數據庫查詢 systemAdmin 用戶
    if username == "systemAdmin":
        try:
            from services.api.services.system_user_store_service import SystemUserStoreService

            service = SystemUserStoreService()
            system_user = service.get_system_user("systemAdmin")

            if system_user is None:
                logger.warning("SystemAdmin user not found in database")
                return None

            if not system_user.is_active:
                logger.warning("SystemAdmin user is inactive")
                return None

            # 驗證密碼
            if not service.verify_password("systemAdmin", password):
                logger.warning("System admin login attempt with incorrect password")
                return None

            # 更新登錄信息（可選，不影響認證流程）
            try:
                from datetime import datetime

                from services.api.models.system_user import SystemUserUpdate

                metadata = system_user.metadata.copy()
                metadata["last_login_at"] = datetime.utcnow().isoformat()
                metadata["login_count"] = metadata.get("login_count", 0) + 1
                service.update_system_user(
                    "systemAdmin",
                    SystemUserUpdate(metadata=metadata),
                )
            except Exception as e:
                logger.warning(f"Failed to update login info: {e}")

            # 創建 User 對象
            return User(
                user_id=system_user.user_id,
                username=system_user.username,
                email=system_user.email,
                roles=system_user.roles,
                permissions=system_user.permissions,
                is_active=system_user.is_active,
                metadata=system_user.metadata,
            )
        except Exception as e:
            logger.error(f"Failed to authenticate systemAdmin: {e}", exc_info=True)
            # 降級到舊的驗證方式（向後兼容）
            if password == os.getenv("SYSTEM_ADMIN_PASSWORD", "systemAdmin@2026"):
                logger.warning("Using fallback authentication for systemAdmin")
                return User.create_system_admin()
            return None

    if username and password:
        # 使用 email 作為 user_id（如果 username 是 email）
        # 否則使用 username 作為 user_id
        user_id = username if "@" in username else f"user_{username}"
        email = username if "@" in username else f"{username}@example.com"

        # 創建一個臨時用戶對象
        # 實際應用中應該從數據庫讀取用戶信息
        # 修改時間：2025-12-09 - 為測試用戶添加文件上傳權限
        return User(
            user_id=user_id,
            username=username,
            email=email,
            roles=["user"],
            permissions=[
                "file:upload",
                "file:read",
                "file:read:own",
                "file:delete:own",
            ],  # 添加基本文件操作權限
            is_active=True,
        )

    return None


@router.post("/login", response_model=LoginResponse)
@audit_log(action=AuditAction.LOGIN, resource_type="auth")
async def login(
    request_data: LoginRequest,
    request: Request,
) -> JSONResponse:
    """用戶登錄端點。

    Args:
        request_data: 登錄請求（包含用戶名和密碼）
        request: FastAPI Request 對象

    Returns:
        包含 access_token 和 refresh_token 的響應
    """
    # 驗證用戶憑證
    user = _authenticate_user(request_data.username, request_data.password)
    if not user:
        return APIResponse.error(
            message="Invalid username or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    if not user.is_active:
        return APIResponse.error(
            message="User account is inactive",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # 生成 Token
    jwt_service = get_jwt_service()

    # 構建 Token payload
    # 修改時間：2025-12-09 - 確保權限列表不為空，添加基本文件操作權限
    permissions = user.permissions or []
    # 如果沒有權限，添加基本文件操作權限（用於測試環境）
    if not permissions:
        permissions = ["file:upload", "file:read", "file:read:own", "file:delete:own"]

    token_data = {
        "sub": user.user_id,
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "permissions": permissions,
        "is_active": user.is_active,
        "metadata": user.metadata,
    }

    # 生成 Access Token 和 Refresh Token
    access_token = jwt_service.create_access_token(data=token_data)
    refresh_token = jwt_service.create_refresh_token(
        data={"sub": user.user_id, "user_id": user.user_id}
    )

    logger.info(
        "User logged in",
        user_id=user.user_id,
        username=user.username,
    )

    response = APIResponse.success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        message="Login successful",
    )

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # 開發環境設為 False，生產環境應為 True
        samesite="lax",
        max_age=86400,  # 24 小時
    )

    return response


@router.post("/refresh", response_model=RefreshTokenResponse)
@audit_log(action=AuditAction.TOKEN_REFRESH, resource_type="auth")
async def refresh_token(
    request_data: RefreshTokenRequest,
    request: Request,
) -> JSONResponse:
    """刷新 Access Token 端點。

    Args:
        request_data: 刷新 Token 請求（包含 refresh_token）
        request: FastAPI Request 對象

    Returns:
        包含新的 access_token 的響應
    """
    jwt_service = get_jwt_service()

    # 驗證 Refresh Token
    payload = jwt_service.verify_token(request_data.refresh_token, token_type="refresh")
    if payload is None:
        return APIResponse.error(
            message="Invalid or expired refresh token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # 從 Refresh Token 獲取用戶 ID
    user_id = payload.get("sub") or payload.get("user_id")
    if not user_id:
        return APIResponse.error(
            message="Invalid token payload",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # TODO: 從數據庫重新加載用戶信息（以獲取最新的角色和權限）
    # 這裡暫時使用 Refresh Token 中的基本信息
    token_data = {
        "sub": user_id,
        "user_id": user_id,
        "username": payload.get("username"),
        "email": payload.get("email"),
        "roles": payload.get("roles", []),
        "permissions": payload.get("permissions", []),
        "is_active": payload.get("is_active", True),
        "metadata": payload.get("metadata", {}),
    }

    # 生成新的 Access Token
    access_token = jwt_service.create_access_token(data=token_data)

    logger.info("Access token refreshed", user_id=user_id)

    return APIResponse.success(
        data=RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
        ),
        message="Token refreshed successfully",
    )


@router.post("/logout")
@audit_log(action=AuditAction.LOGOUT, resource_type="auth")
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """用戶登出端點。

    將當前的 Access Token 加入黑名單。

    Args:
        request: FastAPI Request 對象
        current_user: 當前認證用戶

    Returns:
        登出成功的響應
    """
    # 從請求中提取 Token
    from system.security.auth import extract_token_from_request

    token = await extract_token_from_request(request)
    if token:
        jwt_service = get_jwt_service()
        jwt_service.add_to_blacklist(token)

    logger.info("User logged out", user_id=current_user.user_id)

    return APIResponse.success(
        data={},
        message="Logout successful",
    )


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取當前用戶信息端點。

    Args:
        current_user: 當前認證用戶

    Returns:
        當前用戶信息
    """
    return APIResponse.success(
        data=current_user.to_dict(),
        message="User information retrieved successfully",
    )


class UpdateProfileRequest(BaseModel):
    """更新個人信息請求模型"""

    username: Optional[str] = None
    email: Optional[EmailStr] = None


@router.put("/me")
@audit_log(action=AuditAction.USER_UPDATE, resource_type="user_account")
async def update_current_user_info(
    request_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """更新當前用戶信息端點。

    只允許更新 username 和 email 字段，用戶只能修改自己的信息。

    Args:
        request_data: 更新請求（包含 username 和/或 email）
        current_user: 當前認證用戶

    Returns:
        更新後的用戶信息
    """
    try:
        # 導入 UserAccountStoreService 和相關模型
        from services.api.models.user_account import UserAccountUpdate
        from services.api.services.user_account_store_service import get_user_account_store_service

        # 驗證請求數據不為空
        if not request_data.username and not request_data.email:
            return APIResponse.error(
                message="At least one field (username or email) must be provided",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 構建更新數據（只包含 username 和 email）
        update_data = UserAccountUpdate(
            username=request_data.username,
            email=request_data.email,
        )

        # 獲取 UserAccountStoreService
        service = get_user_account_store_service()

        # 更新用戶信息（使用當前用戶的 user_id）
        updated_user = service.update_user_account(current_user.user_id, update_data)

        if updated_user is None:
            return APIResponse.error(
                message=f"User '{current_user.user_id}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 移除密碼哈希（安全考慮）
        user_dict = updated_user.model_dump(mode="json")
        user_dict.pop("password_hash", None)

        logger.info(
            "User profile updated",
            user_id=current_user.user_id,
            username=updated_user.username,
        )

        return APIResponse.success(
            data=user_dict,
            message="User information updated successfully",
        )
    except ValueError as e:
        # 處理唯一性驗證錯誤或其他驗證錯誤
        error_message = str(e)
        logger.warning(
            "Failed to update user profile",
            user_id=current_user.user_id,
            error=error_message,
        )

        # 檢查是否為唯一性錯誤
        if "already exists" in error_message.lower():
            error_code = (
                "USERNAME_EXISTS" if "username" in error_message.lower() else "EMAIL_EXISTS"
            )
            return APIResponse.error(
                message=error_message,
                error_code=error_code,
                status_code=status.HTTP_409_CONFLICT,
            )

        return APIResponse.error(
            message=error_message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            "Failed to update user profile",
            user_id=current_user.user_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to update user information: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class ChangePasswordRequest(BaseModel):
    """變更密碼請求模型"""

    current_password: str
    new_password: str


@router.post("/change-password")
@audit_log(action=AuditAction.USER_UPDATE, resource_type="user_account")
async def change_password(
    request_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """變更當前用戶密碼端點。

    用戶必須提供當前密碼進行驗證，然後才能設置新密碼。

    Args:
        request_data: 變更密碼請求（包含當前密碼和新密碼）
        current_user: 當前認證用戶

    Returns:
        成功響應
    """
    try:
        # 導入 UserAccountStoreService
        from services.api.services.user_account_store_service import get_user_account_store_service

        # 驗證新密碼長度
        if len(request_data.new_password) < 8:
            return APIResponse.error(
                message="新密碼長度必須至少 8 個字符",
                error_code="PASSWORD_TOO_SHORT",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 檢查新密碼是否與當前密碼相同
        if request_data.current_password == request_data.new_password:
            return APIResponse.error(
                message="新密碼不能與當前密碼相同",
                error_code="PASSWORD_SAME_AS_CURRENT",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 獲取 UserAccountStoreService
        service = get_user_account_store_service()

        # 驗證當前密碼
        if not service.verify_password(current_user.user_id, request_data.current_password):
            logger.warning(
                "Password change attempt with incorrect current password",
                user_id=current_user.user_id,
            )
            return APIResponse.error(
                message="當前密碼錯誤",
                error_code="INVALID_PASSWORD",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 更新密碼
        success = service.reset_password(current_user.user_id, request_data.new_password)

        if not success:
            return APIResponse.error(
                message="密碼更新失敗",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "User password changed successfully",
            user_id=current_user.user_id,
        )

        return APIResponse.success(
            data={},
            message="密碼修改成功",
        )
    except ValueError as e:
        # 處理驗證錯誤
        error_message = str(e)
        logger.warning(
            "Failed to change password",
            user_id=current_user.user_id,
            error=error_message,
        )
        return APIResponse.error(
            message=error_message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(
            "Failed to change password",
            user_id=current_user.user_id,
            error=str(e),
            exc_info=True,
        )
        return APIResponse.error(
            message=f"密碼修改失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
