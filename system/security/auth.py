# 代碼功能說明: 認證相關功能
# 創建日期: 2025-11-26 01:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:30 (UTC+8)

"""認證相關功能 - 包含 JWT 和 API Key 驗證邏輯（預留接口）。

TODO (WBS 1.6.1): 實現 JWT Token 服務
  - JWT 簽發、驗證、刷新功能
  - Token 黑名單管理
  - Token 過期處理

TODO (WBS 1.6.2): 實現 API Key 管理
  - API Key 生成和驗證
  - API Key 輪換機制
  - API Key 限流功能

相關文件：
  - services/security/auth.py (此文件)
  - services/security/jwt_service.py (待創建)
  - services/security/api_key_service.py (待創建)
"""

from fastapi import Request
from typing import Optional

import structlog

from system.security.config import get_security_settings
from system.security.models import User
from system.security.jwt_service import get_jwt_service

logger = structlog.get_logger(__name__)


async def verify_jwt_token(token: str) -> Optional[User]:
    """驗證 JWT Token 並返回用戶信息。

    Args:
        token: JWT Token 字符串

    Returns:
        User 對象，如果驗證失敗則返回 None
    """
    jwt_service = get_jwt_service()
    payload = jwt_service.verify_token(token, token_type="access")

    if payload is None:
        logger.warning(
            "JWT token verification failed",
            token_length=len(token) if token else 0,
            token_preview=token[:20] + "..." if token and len(token) > 20 else token
        )
        return None

    # 從 Token payload 構建 User 對象
    try:
        user_id = payload.get("sub") or payload.get("user_id")
        if not user_id:
            logger.warning("Token payload missing user_id", payload_keys=list(payload.keys()))
            return None

        # 修改時間：2025-12-09 - 如果 JWT token 中沒有權限，添加默認權限
        permissions = payload.get("permissions", [])
        # 如果沒有權限，添加基本文件操作權限（用於測試環境）
        if not permissions:
            permissions = ["file:upload", "file:read", "file:read:own", "file:delete:own"]
        
        user = User(
            user_id=str(user_id),
            username=payload.get("username"),
            email=payload.get("email"),
            roles=payload.get("roles", []),
            permissions=permissions,
            is_active=payload.get("is_active", True),
            metadata=payload.get("metadata", {}),
        )

        logger.debug(
            "JWT token verified successfully",
            user_id=user.user_id,
            username=user.username
        )
        return user

    except Exception as e:
        logger.error("Failed to build User from token payload", error=str(e), exc_info=True)
        return None


async def verify_api_key(api_key: str) -> Optional[User]:
    """驗證 API Key 並返回用戶信息。

    Args:
        api_key: API Key 字符串

    Returns:
        User 對象，如果驗證失敗則返回 None

    TODO (WBS 1.6.2): 實現 API Key 驗證邏輯
      - 查詢 API Key 資料庫
      - 驗證 API Key 有效性（未過期、未撤銷）
      - 檢查 API Key 限流狀態
      - 返回對應用戶信息
    """
    # 目前僅返回 None，表示未實現
    # 後續在 WBS 1.6.2 中實現
    return None


async def extract_token_from_request(request: Request) -> Optional[str]:
    """從請求中提取認證 Token。

    支援從以下位置提取：
    - Authorization header (Bearer token)
    - X-API-Key header (API Key)

    Args:
        request: FastAPI Request 對象

    Returns:
        Token 字符串，如果未找到則返回 None
    """
    # 檢查 Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # 移除 "Bearer " 前綴
        logger.debug("Token extracted from Authorization header", token_length=len(token))
        return token

    # 檢查 X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        logger.debug("API Key extracted from X-API-Key header")
        return api_key

    logger.debug("No token found in request headers")
    return None


async def authenticate_request(request: Request) -> Optional[User]:
    """認證請求並返回用戶信息。

    此函數會嘗試多種認證方式：
    1. JWT Token (如果啟用)
    2. API Key (如果啟用)

    Args:
        request: FastAPI Request 對象

    Returns:
        User 對象，如果認證失敗則返回 None

    """
    settings = get_security_settings()

    # 修改時間：2025-01-27 - 優先從 JWT token 解析用戶信息，即使在開發模式下
    # 提取 Token（即使在開發模式下也嘗試提取）
    token = await extract_token_from_request(request)

    # 如果提供了 token，始終嘗試從 token 中解析用戶信息
    if token:
        # 嘗試 JWT 認證（即使 JWT 被禁用，也嘗試解析）
        user = await verify_jwt_token(token)
        if user:
            logger.debug(
                "User authenticated via JWT token",
                user_id=user.user_id,
                path=request.url.path,
                method=request.method
            )
            return user
        else:
            logger.warning(
                "JWT token verification failed",
                path=request.url.path,
                method=request.method,
                token_length=len(token)
            )

        # 嘗試 API Key 認證
        if settings.api_key.enabled:
            user = await verify_api_key(token)
            if user:
                logger.debug("User authenticated via API Key", user_id=user.user_id)
                return user

    # 修改時間：2025-01-27 - 正式測試：移除 dev_user fallback
    # 只有在 SECURITY_ENABLED=false 時才允許繞過認證
    if settings.should_bypass_auth:
        logger.warning(
            "Security is disabled, allowing unauthenticated access",
            path=request.url.path,
            method=request.method,
            has_token=bool(token)
        )
        # 返回一個臨時用戶（用於測試，但不會使用 dev_user）
        return User(
            user_id="unauthenticated",
            username="unauthenticated",
            email=None,
            roles=[],
            permissions=[],
            is_active=True,
            metadata={"bypass_auth": True},
        )

    # 正式測試環境：認證失敗返回 None
    logger.debug(
        "No valid token and security enabled, returning None",
        path=request.url.path,
        method=request.method
    )
    return None
