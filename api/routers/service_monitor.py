# 代碼功能說明: 服務監控路由
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 19:36 UTC+8

"""服務監控路由 - 提供服務狀態查詢和管理 API"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlencode

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, JSONResponse, Response

from api.core.response import APIResponse
from api.core.version import API_PREFIX
from services.api.models.audit_log import AuditAction
from services.api.services.service_monitor_service import get_service_monitor_service
from services.api.services.service_status_store_service import get_service_status_store_service
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.jwt_service import get_jwt_service
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/services", tags=["Service Monitor"])

# 功能開關：是否使用新的 Prometheus 監控系統
USE_NEW_MONITORING = os.getenv("USE_NEW_MONITORING", "false").lower() == "true"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

# RQ Dashboard 代理基礎路徑（用於 list_dashboards url 與 HTML 靜態資源重寫）
RQ_DASHBOARD_PROXY_BASE = f"{API_PREFIX}/admin/services/dashboards/rq"

# 常用靜態檔 MIME（僅列部分，其餘由 FileResponse 推測）
_RQ_STATIC_MEDIA = {
    ".css": "text/css",
    ".js": "application/javascript",
    ".ico": "image/vnd.microsoft.icon",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
}


def _get_rq_dashboard_static_dir() -> Optional[Path]:
    """取得 rq_dashboard 套件 static 目錄；未安裝則回傳 None。"""
    try:
        import rq_dashboard

        d = Path(rq_dashboard.__file__).resolve().parent / "static"
        return d if d.is_dir() else None
    except Exception:
        return None


async def get_user_for_rq_dashboard(
    request: Request,
    token: Optional[str] = Query(None, alias="token"),
) -> User:
    """從 URL ?token=、Cookie 或 Authorization 取得用戶，供 RQ Dashboard 代理（iframe）使用。"""
    from system.security.config import get_security_settings

    settings = get_security_settings()
    if settings.should_bypass_auth:
        return User.create_system_admin()

    token_value = token
    if not token_value:
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer "):
            token_value = auth[7:]
        elif request.cookies.get("access_token"):
            token_value = request.cookies.get("access_token")

    if not token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required (token, cookie, or Authorization header)",
        )

    jwt_service = get_jwt_service()
    payload = jwt_service.verify_token(token_value, token_type="access")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = User(
        user_id=payload.get("user_id") or payload.get("sub") or "unknown",
        username=payload.get("username") or "unknown",
        email=payload.get("email") or "unknown@local",
        roles=payload.get("roles", []),
        permissions=payload.get("permissions", []),
        is_active=payload.get("is_active", True),
        metadata=payload.get("metadata", {}),
    )

    if settings.rbac.enabled and not user.has_permission(Permission.ALL.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: system_admin",
        )
    return user


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
async def list_services(
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取所有服務狀態列表

    根據 USE_NEW_MONITORING 環境變量決定使用舊系統（ArangoDB）還是新系統（Prometheus）。

    Args:
        current_user: 當前認證用戶

    Returns:
        所有服務的當前狀態
    """
    try:
        # 如果啟用新監控系統，從 Prometheus 獲取數據
        if USE_NEW_MONITORING:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{PROMETHEUS_URL}/api/v1/query",
                        params={"query": "up"},
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("status") == "success":
                        results = data.get("data", {}).get("result", [])
                        services = []

                        for result in results:
                            metric = result.get("metric", {})
                            value = result.get("value", [None, None])[1]

                            if value is None:
                                continue

                            try:
                                up_value = float(value)
                            except (ValueError, TypeError):
                                continue

                            job_name = metric.get("job", "unknown")
                            instance = metric.get("instance", "unknown")
                            service_name = metric.get("service") or job_name

                            host = instance.split(":")[0] if ":" in instance else instance
                            port = None
                            if ":" in instance:
                                try:
                                    port = int(instance.split(":")[1])
                                except ValueError:
                                    pass

                            status_val = "running" if up_value == 1 else "stopped"
                            health_status = "healthy" if up_value == 1 else "unhealthy"

                            service_dict = {
                                "service_name": service_name,
                                "service_type": metric.get("component", "unknown"),
                                "status": status_val,
                                "health_status": health_status,
                                "host": host,
                                "port": port,
                                "check_interval": 15,
                                "last_check_at": datetime.now(timezone.utc).isoformat(),
                                "last_success_at": (
                                    datetime.now(timezone.utc).isoformat()
                                    if up_value == 1
                                    else None
                                ),
                                "metadata": {
                                    "prometheus_job": job_name,
                                    "prometheus_instance": instance,
                                    "labels": metric,
                                    "source": "prometheus",
                                },
                            }
                            services.append(service_dict)

                        return APIResponse.success(
                            data={"services": services, "total": len(services)},
                            message="Services retrieved successfully from Prometheus",
                        )
                    else:
                        logger.warning(
                            f"Prometheus query failed: {data.get('error', 'Unknown error')}"
                        )
                        # 降級到舊系統
            except Exception as e:
                logger.warning(
                    f"Failed to fetch from Prometheus, falling back to old system: {str(e)}"
                )
                # 降級到舊系統

        # 使用舊系統（ArangoDB）
        store_service = get_service_status_store_service()
        services = store_service.list_all_services()

        service_dicts = [service.model_dump(mode="json") for service in services]

        return APIResponse.success(
            data={"services": service_dicts, "total": len(service_dicts)},
            message="Services retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list services: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list services: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{service_name}", status_code=status.HTTP_200_OK)
async def get_service_status(
    service_name: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取特定服務狀態詳情

    Args:
        service_name: 服務名稱
        current_user: 當前認證用戶

    Returns:
        服務狀態詳情
    """
    try:
        store_service = get_service_status_store_service()
        service = store_service.get_service_status(service_name)

        if service is None:
            return APIResponse.error(
                message=f"Service '{service_name}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(
            data=service.model_dump(mode="json"),
            message="Service status retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get service status: service_name={service_name}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get service status: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{service_name}/history", status_code=status.HTTP_200_OK)
async def get_service_history(
    service_name: str,
    start_time: Optional[str] = Query(default=None, description="開始時間（ISO 8601 格式）"),
    end_time: Optional[str] = Query(default=None, description="結束時間（ISO 8601 格式）"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取服務狀態歷史記錄

    Args:
        service_name: 服務名稱
        start_time: 開始時間
        end_time: 結束時間
        limit: 限制返回數量
        current_user: 當前認證用戶

    Returns:
        服務狀態歷史記錄
    """
    try:
        store_service = get_service_status_store_service()

        # 解析時間參數
        start_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                return APIResponse.error(
                    message="Invalid start_time format. Use ISO 8601 format.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        end_dt = None
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                return APIResponse.error(
                    message="Invalid end_time format. Use ISO 8601 format.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        history = store_service.get_service_history(
            service_name=service_name,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
        )

        history_dicts = [h.model_dump(mode="json") for h in history]

        return APIResponse.success(
            data={"history": history_dicts, "total": len(history_dicts)},
            message="Service history retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get service history: service_name={service_name}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get service history: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{service_name}/check", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="service",
    get_resource_id=lambda service_name: service_name,
)
async def check_service(
    service_name: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    手動觸發服務健康檢查

    Args:
        service_name: 服務名稱
        current_user: 當前認證用戶

    Returns:
        檢查結果
    """
    try:
        monitor_service = get_service_monitor_service()
        store_service = get_service_status_store_service()

        # 執行健康檢查
        check_result = await monitor_service.check_service(service_name)

        # 更新服務狀態
        updated_status = store_service.update_service_status(
            service_name=service_name,
            status=check_result.status,
            health_status=check_result.health_status,
            metadata=check_result.metadata or {},
        )

        result_dict = {
            "service_name": check_result.service_name,
            "status": check_result.status,
            "health_status": check_result.health_status,
            "response_time_ms": check_result.response_time_ms,
            "error_message": check_result.error_message,
            "metadata": check_result.metadata,
            "updated_status": updated_status.model_dump(mode="json"),
        }

        logger.info(
            f"Service check completed: service_name={service_name}, status={check_result.status}"
        )

        return APIResponse.success(
            data=result_dict,
            message="Service check completed successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to check service: service_name={service_name}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to check service: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{service_name}/metrics", status_code=status.HTTP_200_OK)
async def get_service_metrics(
    service_name: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取服務指標

    Args:
        service_name: 服務名稱
        current_user: 當前認證用戶

    Returns:
        服務指標
    """
    try:
        store_service = get_service_status_store_service()
        service = store_service.get_service_status(service_name)

        if service is None:
            return APIResponse.error(
                message=f"Service '{service_name}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 從 metadata 中提取指標
        metadata = service.metadata or {}
        metrics = {
            "service_name": service_name,
            "cpu_usage": metadata.get("cpu_usage"),
            "memory_usage": metadata.get("memory_usage"),
            "request_count": metadata.get("request_count"),
            "error_count": metadata.get("error_count"),
            "response_time_avg": metadata.get("response_time_avg"),
            "uptime": metadata.get("uptime"),
            "timestamp": datetime.utcnow().isoformat(),
        }

        return APIResponse.success(
            data=metrics,
            message="Service metrics retrieved successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to get service metrics: service_name={service_name}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get service metrics: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/dashboards", status_code=status.HTTP_200_OK)
async def list_dashboards(
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取可用的服務 Dashboard 列表

    Args:
        current_user: 當前認證用戶

    Returns:
        Dashboard 列表
    """
    try:
        dashboards = [
            {
                "name": "rq",
                "display_name": "RQ Dashboard",
                "description": "Redis Queue 任務監控儀表板",
                "type": "proxy",
                "url": RQ_DASHBOARD_PROXY_BASE,
                "external_url": "http://localhost:9181",
                "icon": "queue",
            },
            {
                "name": "arangodb",
                "display_name": "ArangoDB Web UI",
                "description": "ArangoDB 數據庫管理界面",
                "type": "external",
                "external_url": "http://localhost:8529",
                "icon": "database",
            },
            {
                "name": "seaweedfs",
                "display_name": "SeaweedFS Dashboard",
                "description": "SeaweedFS 分布式文件系統儀表板",
                "type": "external",
                "external_url": "http://localhost:9333",
                "icon": "storage",
            },
        ]

        logger.info(f"Dashboards list retrieved: count={len(dashboards)}")

        return APIResponse.success(
            data={"dashboards": dashboards, "total": len(dashboards)},
            message="Dashboards retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list dashboards: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list dashboards: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _rewrite_rq_dashboard_html(html: str, base: str, token: Optional[str] = None) -> str:
    """將 RQ Dashboard HTML 內根路徑 href/src 改為 proxy 路徑，避免靜態資源 404。"""
    base_slash = base.rstrip("/") + "/"
    safe_base = re.escape(base_slash)
    suffix = f"?token={token}" if token else ""
    # 只改寫 href="/path" / src="/path"（不含 // 或已為 base 前綴），保留 path
    pattern = r'(href|src)=(["\'])/(?!' + safe_base + r'|/)([^"\']*)\2'
    return re.sub(pattern, r"\1=\2" + base_slash + r"\3" + suffix + r"\2", html)


@router.get("/dashboards/rq/{path:path}", status_code=status.HTTP_200_OK)
@router.post("/dashboards/rq/{path:path}", status_code=status.HTTP_200_OK)
async def proxy_rq_dashboard(
    request: Request,
    path: str = "",
    token: Optional[str] = Query(None, alias="token"),
    current_user: User = Depends(get_user_for_rq_dashboard),
) -> Response:
    """
    代理 RQ Dashboard 訪問。支援 ?token=、Cookie、Authorization（供 iframe 使用）。

    HTML 回應會重寫 href/src 根路徑為 proxy 路徑，避免靜態資源 404；
    若有 token 則附加至改寫後 URL，使靜態請求也通過認證。
    """
    try:
        # 靜態資源改由我們從 rq_dashboard 套件提供，不轉發 9181（9181 常 404）
        if request.method == "GET" and path.startswith("static/"):
            static_dir = _get_rq_dashboard_static_dir()
            if static_dir is not None:
                sub = path[len("static/") :].lstrip("/")
                if not sub or ".." in sub:
                    raise HTTPException(status_code=400, detail="Invalid static path")
                fp = (static_dir / sub).resolve()
                if not str(fp).startswith(str(static_dir.resolve())):
                    raise HTTPException(status_code=400, detail="Invalid static path")
                if fp.is_file():
                    media = _RQ_STATIC_MEDIA.get(fp.suffix)
                    return FileResponse(fp, media_type=media)

        rq_dashboard_url = "http://localhost:9181"
        target_url = f"{rq_dashboard_url}/{path}"

        qs = parse_qs(request.url.query)
        qs.pop("token", None)
        query_string = urlencode(qs, doseq=True)
        if query_string:
            target_url += f"?{query_string}"

        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("authorization", None)
        headers.pop("accept-encoding", None)

        body = None
        if request.method == "POST":
            body = await request.body()

        async with httpx.AsyncClient(timeout=30.0) as client:
            if request.method == "GET":
                proxy_response = await client.get(target_url, headers=headers)
            elif request.method == "POST":
                proxy_response = await client.post(target_url, headers=headers, content=body)
            else:
                return Response(
                    content="Method not allowed",
                    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                )

        out_headers = dict(proxy_response.headers)
        content = proxy_response.content
        ct = (out_headers.get("content-type") or "").lower()

        if proxy_response.status_code == 200 and "text/html" in ct and isinstance(content, bytes):
            try:
                text = content.decode("utf-8")
                rewritten = _rewrite_rq_dashboard_html(text, RQ_DASHBOARD_PROXY_BASE, token=token)
                content = rewritten.encode("utf-8")
                out_headers["content-length"] = str(len(content))
                out_headers.pop("content-encoding", None)
            except Exception as e:
                logger.warning("RQ Dashboard HTML rewrite failed: %s", e)

        return Response(
            content=content,
            status_code=proxy_response.status_code,
            headers=out_headers,
        )

    except httpx.TimeoutException:
        logger.error(f"RQ Dashboard proxy timeout: path={path}")
        return Response(
            content="RQ Dashboard is not responding",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except httpx.RequestError as e:
        logger.error(f"RQ Dashboard proxy error: path={path}, error={str(e)}", exc_info=True)
        return Response(
            content="Failed to connect to RQ Dashboard",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as e:
        logger.error(f"Failed to proxy RQ Dashboard: path={path}, error={str(e)}", exc_info=True)
        return Response(
            content=f"Failed to proxy RQ Dashboard: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{service_name}/logs", status_code=status.HTTP_200_OK)
async def get_service_logs(
    service_name: str,
    start_time: Optional[str] = Query(default=None, description="開始時間（ISO 8601 格式）"),
    end_time: Optional[str] = Query(default=None, description="結束時間（ISO 8601 格式）"),
    log_level: Optional[str] = Query(
        default=None, description="日誌級別（DEBUG/INFO/WARNING/ERROR/CRITICAL）"
    ),
    keyword: Optional[str] = Query(default=None, description="關鍵字搜索"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取服務日誌

    Args:
        service_name: 服務名稱
        start_time: 開始時間
        end_time: 結束時間
        log_level: 日誌級別
        keyword: 關鍵字搜索
        limit: 限制返回數量
        current_user: 當前認證用戶

    Returns:
        服務日誌列表
    """
    try:
        from services.api.services.service_log_store_service import get_service_log_store_service

        log_service = get_service_log_store_service()

        # 解析時間參數
        start_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                return APIResponse.error(
                    message="Invalid start_time format. Use ISO 8601 format.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        end_dt = None
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                return APIResponse.error(
                    message="Invalid end_time format. Use ISO 8601 format.",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # 查詢日誌
        logs = log_service.get_service_logs(
            service_name=service_name,
            start_time=start_dt,
            end_time=end_dt,
            log_level=log_level,
            keyword=keyword,
            limit=limit,
        )

        logs_dicts = [log.model_dump(mode="json") for log in logs]

        logger.info(f"Service logs retrieved: service_name={service_name}, count={len(logs_dicts)}")

        return APIResponse.success(
            data={"logs": logs_dicts, "total": len(logs_dicts)},
            message="Service logs retrieved successfully",
        )

    except Exception as e:
        logger.error(
            f"Failed to get service logs: service_name={service_name}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get service logs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{service_name}/logs/collect", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="service_log",
    get_resource_id=lambda service_name: service_name,
)
async def collect_service_logs(
    service_name: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    手動觸發服務日誌收集

    Args:
        service_name: 服務名稱
        current_user: 當前認證用戶

    Returns:
        收集結果
    """
    try:
        from services.api.services.service_log_collector import get_service_log_collector

        collector = get_service_log_collector()

        # 執行日誌收集
        collected_count = await collector.collect_service_logs(service_name)

        logger.info(f"Service logs collected: service_name={service_name}, count={collected_count}")

        return APIResponse.success(
            data={
                "service_name": service_name,
                "collected_count": collected_count,
                "timestamp": datetime.utcnow().isoformat(),
            },
            message=f"Successfully collected {collected_count} log entries",
        )

    except Exception as e:
        logger.error(
            f"Failed to collect service logs: service_name={service_name}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to collect service logs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
