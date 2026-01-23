# 代碼功能說明: OAuth2 認證路由
# 創建日期: 2026-01-18 14:09 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 14:09 UTC+8

"""OAuth2 認證路由 - 為 Grafana 和 Prometheus 提供 SSO"""

import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jwt
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.core.response import APIResponse
from system.security.dependencies import get_current_user
from system.security.models import Role

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/oauth2", tags=["OAuth2 SSO"])

# OAuth2 配置
OAUTH2_CLIENT_ID = "ai-box-oauth2-client"
OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", "CHANGE_THIS_TO_CLIENT_SECRET")
OAUTH2_ISSUER_URL = "http://localhost:8000"
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-here-change-in-production")

# 儲存授權碼（實際生產應使用 Redis 或數據庫）
auth_codes: Dict[str, Dict] = {}

# 儲存 refresh tokens
refresh_tokens: Dict[str, str] = {}


class AuthorizationRequest(BaseModel):
    """授權請求"""

    response_type: str = "code"
    client_id: str
    redirect_uri: str
    scope: str = "openid email profile"
    state: str


class TokenRequest(BaseModel):
    """令牌請求"""

    grant_type: str = "authorization_code"
    code: str
    client_id: str
    client_secret: str
    redirect_uri: str


class TokenResponse(BaseModel):
    """令牌響應"""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    id_token: Optional[str] = None


class UserInfo(BaseModel):
    """用戶信息"""

    sub: str
    name: str
    email: str
    email_verified: bool = True
    roles: List[str]
    given_name: Optional[str] = None
    family_name: Optional[str] = None


class JWKSResponse(BaseModel):
    """JWKS 響應"""

    keys: List[Dict]


@router.get("/authorize", status_code=status.HTTP_200_OK)
async def authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    scope: str = "openid email profile",
    state: Optional[str] = None,
    current_user=Depends(get_current_user),
) -> Response:
    """
    OAuth2 授權端點

    Args:
        client_id: 客戶端 ID
        redirect_uri: 重定向 URI
        response_type: 響應類型（默認 code）
        scope: 授權範圍
        state: 狀態值
        current_user: 當前認證用戶

    Returns:
        重定向到客戶端或授權頁面
    """
    try:
        # 驗證客戶端 ID
        if client_id != OAUTH2_CLIENT_ID:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid client_id")

        # 檢查用戶是否是 system_admin
        if not current_user.has_role(Role.SYSTEM_ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system_admin can access monitoring tools",
            )

        # 生成授權碼
        auth_code = secrets.token_urlsafe(32)
        auth_codes[auth_code] = {
            "user_id": current_user.user_id,
            "username": current_user.username,
            "email": current_user.email,
            "roles": current_user.roles,
            "expires_at": datetime.utcnow() + timedelta(minutes=10),
            "redirect_uri": redirect_uri,
        }

        logger.info(
            f"OAuth2 authorization granted to user {current_user.user_id}",
            user_id=current_user.user_id,
            roles=current_user.roles,
        )

        # 構建重定向 URL
        redirect_url = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_url += f"&state={state}"

        return Response(status_code=status.HTTP_302_FOUND, headers={"Location": redirect_url})

    except Exception as e:
        logger.error(f"OAuth2 authorization failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authorization failed: {str(e)}",
        )


@router.post("/token", status_code=status.HTTP_200_OK)
async def token(request: TokenRequest) -> TokenResponse:
    """
    OAuth2 令牌端點

    Args:
        request: 令牌請求

    Returns:
        訪問令牌和刷新令牌
    """
    try:
        # 驗證客戶端
        if request.client_id != OAUTH2_CLIENT_ID or request.client_secret != OAUTH2_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid client credentials"
            )

        # 查詢授權碼
        auth_info = auth_codes.get(request.code)
        if not auth_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authorization code",
            )

        # 檢查授權碼是否過期
        if datetime.utcnow() > auth_info["expires_at"]:
            del auth_codes[request.code]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Authorization code has expired"
            )

        # 檢查是否是 system_admin
        if Role.SYSTEM_ADMIN.value not in auth_info["roles"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system_admin can access monitoring tools",
            )

        # 生成 JWT access token
        access_token_payload = {
            "sub": auth_info["user_id"],
            "name": auth_info["username"],
            "email": auth_info["email"],
            "roles": auth_info["roles"],
            "iss": OAUTH2_ISSUER_URL,
            "aud": OAUTH2_ISSUER_URL,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 小時過期
        }

        access_token = jwt.encode(access_token_payload, JWT_SECRET, algorithm="HS256")

        # 生成 refresh token
        refresh_token = secrets.token_urlsafe(32)
        refresh_tokens[refresh_token] = auth_info["user_id"]

        # 清理授權碼
        del auth_codes[request.code]

        logger.info(
            f"OAuth2 token issued to user {auth_info['user_id']}",
            user_id=auth_info["user_id"],
            roles=auth_info["roles"],
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=3600,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth2 token generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token generation failed: {str(e)}",
        )


@router.get("/userinfo", status_code=status.HTTP_200_OK)
async def userinfo(request: Request) -> UserInfo:
    """
    OAuth2 用戶信息端點

    Args:
        request: FastAPI 請求對象

    Returns:
        用戶信息
    """
    try:
        # 從請求頭中提取 Bearer token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
            )

        token = auth_header[7:]  # 移除 "Bearer " 前綴

        # 驗證 JWT token
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        # 檢查是否是 system_admin
        if Role.SYSTEM_ADMIN.value not in payload.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system_admin can access monitoring tools",
            )

        # 構建用戶信息
        user_info = UserInfo(
            sub=payload["sub"],
            name=payload.get("name", payload["sub"]),
            email=payload.get("email", ""),
            roles=payload.get("roles", []),
        )

        return user_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OAuth2 userinfo failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Userinfo failed: {str(e)}"
        )


@router.get("/jwks", status_code=status.HTTP_200_OK)
async def jwks() -> JWKSResponse:
    """
    JWKS 端點 - 提供 JSON Web Key Set

    Returns:
        JWKS 響應
    """
    try:
        # 為簡單的 HMAC 使用，我們提供一個空的 JWKS
        # 實際生產應使用 RS256 和真實的 JWKS
        # 這裡返回一個占位符，oauth2-proxy 使用 skip_oidc_discovery=true

        return JWKSResponse(keys=[])

    except Exception as e:
        logger.error(f"JWKS generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"JWKS failed: {str(e)}"
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    current_user=Depends(get_current_user),
) -> JSONResponse:
    """
    OAuth2 登出端點

    Args:
        request: FastAPI 請求對象
        current_user: 當前認證用戶

    Returns:
        成功響應
    """
    try:
        # 清理 refresh tokens
        tokens_to_remove = [
            token for token, user_id in refresh_tokens.items() if user_id == current_user.user_id
        ]
        for token in tokens_to_remove:
            del refresh_tokens[token]

        logger.info(
            f"User {current_user.user_id} logged out from OAuth2",
            user_id=current_user.user_id,
        )

        return APIResponse.success(message="Logged out successfully")

    except Exception as e:
        logger.error(f"OAuth2 logout failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Logout failed: {str(e)}"
        )


# 清理過期的授權碼和刷新令牌
@router.on_event("startup")
async def cleanup_expired_tokens():
    """定時清理過期的令牌"""
    import asyncio

    async def cleanup():
        while True:
            try:
                current_time = datetime.utcnow()

                # 清理過期的授權碼
                expired_codes = [
                    code for code, data in auth_codes.items() if data["expires_at"] < current_time
                ]
                for code in expired_codes:
                    del auth_codes[code]

                # 這裡可以添加刷新令牌的清理邏輯

                if expired_codes:
                    logger.info(f"Cleaned up {len(expired_codes)} expired auth codes")

            except Exception as e:
                logger.error(f"Token cleanup failed: {str(e)}", exc_info=True)

            # 每 10 分鐘清理一次
            await asyncio.sleep(600)

    # 啟動後台任務
    asyncio.create_task(cleanup())
