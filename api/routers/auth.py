# 代碼功能說明: 認證路由
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-08 09:15:21 UTC+8

"""認證路由 - 提供登錄、Token刷新、登出等功能。"""

from typing import Optional
from fastapi import APIRouter, status, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from api.core.response import APIResponse
from system.security.jwt_service import get_jwt_service
from system.security.dependencies import get_current_user
from system.security.models import User
from system.security.config import get_security_settings
from system.security.audit_decorator import audit_log
from services.api.models.audit_log import AuditAction

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
    settings = get_security_settings()

    # 修改時間：2025-12-08 09:15:21 UTC+8 - 修復開發模式下的用戶認證，使用實際用戶 ID
    # 開發模式下，接受任何用戶名/密碼組合，但使用實際的用戶名/email 作為 user_id
    # TODO: 實現真實的用戶認證邏輯
    # 這裡暫時實現一個簡單的驗證（僅用於演示）
    # 在生產環境中，應該從數據庫查詢用戶並驗證密碼
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
            permissions=["file:upload", "file:read", "file:read:own", "file:delete:own"],  # 添加基本文件操作權限
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

    return APIResponse.success(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        message="Login successful",
    )


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
