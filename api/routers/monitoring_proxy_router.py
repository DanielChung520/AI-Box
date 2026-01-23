# 代碼功能說明: 監控代理路由
# 創建日期: 2026-01-18 14:09 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-19 12:30 UTC+8

"""監控代理路由 - 為 Prometheus 和 Grafana 提供安全的訪問代理"""

from typing import Optional

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from system.security.jwt_service import get_jwt_service
from system.security.models import Role, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/monitoring", tags=["Monitoring Proxy"])

# 監控服務 URL
GRAFANA_URL = "http://localhost:3001"
PROMETHEUS_URL = "http://localhost:9090"

# 允許的路徑模式
ALLOWED_GRAFANA_PATHS = [
    "/d/",  # Dashboard
    "/api/datasources/",  # Data sources
    "/api/dashboards/",  # Dashboards
    "/api/user/preferences",  # User preferences
]

ALLOWED_PROMETHEUS_PATHS = [
    "/graph",  # Graph
    "/api/v1/query",  # Query API
    "/api/v1/query_range",  # Query range API
]


def get_user_from_cookie_or_header(
    request: Request,
    path: str = "",
    token: Optional[str] = Query(None),
) -> Optional[User]:
    """從 Cookie、Authorization Header 或 URL 參數獲取當前用戶（用於 iframe SSO）

    對於 Grafana 的公共資源（static files, public/），返回 None
    """
    jwt_service = get_jwt_service()

    token_value = None

    # 嘗試從 URL 參數獲取 token（用於 iframe）
    if token:
        token_value = token
    # Grafana 公共資源不需要認證（僅當沒有 token 時）
    elif path.startswith("public/") or path.startswith("assets/"):
        return None
    # 嘗試從 Authorization header 獲取 token
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token_value = auth_header.split(" ")[1]
        # 嘗試從 cookie 獲取 token
        elif request.cookies.get("access_token"):
            token_value = request.cookies.get("access_token")
        # 如果沒有 token，返回 None（允許訪問 Grafana 登錄頁面）
        else:
            return None

    jwt_service = get_jwt_service()

    token_value = None

    # 嘗試從 URL 參數獲取 token（用於 iframe）
    if token:
        token_value = token
    # 嘗試從 Authorization header 獲取 token
    else:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token_value = auth_header.split(" ")[1]
        # 嘗試從 cookie 獲取 token
        elif request.cookies.get("access_token"):
            token_value = request.cookies.get("access_token")

    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    payload = jwt_service.verify_token(token_value, token_type="access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return User(
        user_id=payload.get("user_id") or payload.get("sub") or "unknown",
        username=payload.get("username") or "unknown",
        email=payload.get("email") or "unknown@local",
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        is_active=payload.get("is_active", True),
        metadata=payload.get("metadata", {}),
    )


@router.api_route(
    "/grafana/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_grafana(
    path: str,
    request: Request,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_user_from_cookie_or_header),
) -> Response:
    """
    Grafana 代理端點 - 只有 system_admin 可以訪問

    Args:
        path: Grafana 路徑
        request: FastAPI 請求對象
        token: 從 URL 參數傳遞的 JWT token
        current_user: 當前認證用戶（可為 None，表示公共資源）

    Returns:
        代理響應
    """
    try:
        # 檢查權限（僅當用戶不為 None 時）
        if current_user and not current_user.has_role(Role.SYSTEM_ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Only system_admin can access Grafana"
            )

        # 構建目標 URL
        url = f"{GRAFANA_URL}/{path}"
        if request.query_params and "token" not in request.query_params:
            # 除去 token 參數的查詢參數
            query_params = {k: v for k, v in request.query_params.items() if k != "token"}
            if query_params:
                url += f"?{request.url.query}"
        else:
            # 移除 token 參數
            if request.query_params:
                query_params = {k: v for k, v in request.query_params.items() if k != "token"}
                if query_params:
                    url += f"?{'&'.join(f'{k}={v}' for k, v in query_params.items())}"

        # 代理請求
        async with httpx.AsyncClient() as client:
            # 轉發請求頭
            headers = dict(request.headers)
            headers.pop("host", None)  # 移除 host 頭

            # 添加 SSO 認證頭（僅當用戶不為 None 時）
            if current_user:
                headers["X-Auth-User"] = current_user.username or current_user.user_id or "admin"
                headers["X-Auth-Email"] = current_user.email or "admin@local"
                headers["X-Auth-Roles"] = (
                    "Admin" if current_user.has_role(Role.SYSTEM_ADMIN.value) else "Viewer"
                )

            # 發送請求
            upstream_response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
                timeout=30.0,
            )

        logger.info(
            f"Proxied request to Grafana: {request.method} /{path}",
            user_id=current_user.user_id if current_user else "public",
            status_code=upstream_response.status_code,
        )

        # 返回響應
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=dict(upstream_response.headers),
            media_type=upstream_response.headers.get("content-type"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Grafana proxy failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Proxy failed: {str(e)}"
        )


@router.api_route(
    "/prometheus/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
)
async def proxy_prometheus(
    path: str,
    request: Request,
    token: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(
        lambda r: get_user_from_cookie_or_header(r, path="", token=None)
    ),
) -> Response:
    """
    Prometheus 代理端點 - 只有 system_admin 可以訪問

    Args:
        path: Prometheus 路徑
        request: FastAPI 請求對象
        current_user: 當前認證用戶

    Returns:
        代理響應
    """
    try:
        # 檢查權限
        if not current_user or not current_user.has_role(Role.SYSTEM_ADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only system_admin can access Prometheus",
            )

        # 構建目標 URL
        url = f"{PROMETHEUS_URL}/{path}"
        if request.query_params:
            query_params = {k: v for k, v in request.query_params.items() if k != "token"}
            if query_params:
                url += f"?{request.url.query}"

        # 代理請求
        async with httpx.AsyncClient() as client:
            # 轉發請求頭
            headers = dict(request.headers)
            headers.pop("host", None)  # 移除 host 頭

            # 發送請求
            upstream_response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
                timeout=30.0,
            )

        logger.info(
            f"Proxied request to Prometheus: {request.method} /{path}",
            user_id=current_user.user_id,
            status_code=upstream_response.status_code,
        )

        # 返回響應
        return Response(
            content=upstream_response.content,
            status_code=upstream_response.status_code,
            headers=dict(upstream_response.headers),
            media_type=upstream_response.headers.get("content-type"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Prometheus proxy failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Proxy failed: {str(e)}"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """健康檢查端點"""
    return APIResponse.success(
        data={"status": "healthy", "services": ["grafana", "prometheus"]},
        message="Monitoring proxy is healthy",
    )
