# 代碼功能說明: Prometheus 兼容層 API
# 創建日期: 2026-01-18 18:29 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 19:36 UTC+8

"""Prometheus 兼容層 API - 提供與舊系統兼容的服務狀態 API，從 Prometheus 獲取數據"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/services", tags=["Prometheus Compat"])

# Prometheus URL（從環境變量獲取，默認 localhost:9090）
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")


# 創建需要系統管理員權限的依賴函數
async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    """檢查用戶是否擁有系統管理員權限的依賴函數"""
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


async def query_prometheus(query: str) -> List[Dict[str, Any]]:
    """
    查詢 Prometheus

    Args:
        query: PromQL 查詢語句

    Returns:
        查詢結果列表
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "success":
                result = data.get("data", {}).get("result", [])
                return result
            else:
                logger.error(f"Prometheus query failed: {data.get('error', 'Unknown error')}")
                return []
    except Exception as e:
        logger.error(f"Failed to query Prometheus: {str(e)}", exc_info=True)
        return []


def _map_prometheus_to_service_status(
    job_name: str, instance: str, up_value: float, labels: Dict[str, Any]
) -> Dict[str, Any]:
    """
    將 Prometheus 數據映射為舊系統的服務狀態格式

    Args:
        job_name: Prometheus job 名稱
        instance: 實例地址
        up_value: up 指標值（1 = 運行中，0 = 離線）
        labels: 標籤字典

    Returns:
        服務狀態字典
    """
    # 提取服務名稱（從 job 或 service 標籤）
    service_name = labels.get("service") or job_name

    # 解析主機和端口
    host = instance.split(":")[0] if ":" in instance else instance
    port = None
    if ":" in instance:
        try:
            port = int(instance.split(":")[1])
        except ValueError:
            pass

    # 確定狀態
    status = "running" if up_value == 1 else "stopped"
    health_status = "healthy" if up_value == 1 else "unhealthy"

    # 構建服務狀態對象
    service_status = {
        "service_name": service_name,
        "service_type": labels.get("component", "unknown"),
        "status": status,
        "health_status": health_status,
        "host": host,
        "port": port,
        "check_interval": 15,  # Prometheus 默認抓取間隔
        "last_check_at": datetime.now(timezone.utc).isoformat(),
        "last_success_at": datetime.now(timezone.utc).isoformat() if up_value == 1 else None,
        "metadata": {
            "prometheus_job": job_name,
            "prometheus_instance": instance,
            "labels": labels,
            "source": "prometheus",
        },
    }

    return service_status


@router.get("/prometheus", status_code=status.HTTP_200_OK)
async def list_services_from_prometheus(
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    從 Prometheus 獲取所有服務狀態列表（兼容舊系統 API 格式）

    此端點從 Prometheus 查詢服務狀態，並轉換為與舊系統兼容的格式。

    Args:
        current_user: 當前認證用戶

    Returns:
        所有服務的當前狀態（兼容舊系統格式）
    """
    try:
        # 查詢 Prometheus 的 up 指標（所有 targets）
        query = "up"
        results = await query_prometheus(query)

        services = []
        for result in results:
            try:
                metric = result.get("metric", {})
                value = result.get("value", [None, None])[1]  # 獲取值（第二個元素）

                if value is None:
                    continue

                try:
                    up_value = float(value)
                except (ValueError, TypeError):
                    continue

                # 提取 job 和 instance
                job_name = metric.get("job", "unknown")
                instance = metric.get("instance", "unknown")

                # 映射為服務狀態
                service_status = _map_prometheus_to_service_status(
                    job_name, instance, up_value, metric
                )
                services.append(service_status)

            except Exception as e:
                logger.warning(f"Failed to process Prometheus result: {str(e)}")
                continue

        return APIResponse.success(
            data={"services": services, "total": len(services)},
            message="Services retrieved successfully from Prometheus",
        )

    except Exception as e:
        logger.error(f"Failed to list services from Prometheus: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list services from Prometheus: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/prometheus/{service_name}", status_code=status.HTTP_200_OK)
async def get_service_status_from_prometheus(
    service_name: str,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    從 Prometheus 獲取特定服務狀態詳情（兼容舊系統 API 格式）

    Args:
        service_name: 服務名稱（對應 Prometheus 的 service 標籤或 job 名稱）
        current_user: 當前認證用戶

    Returns:
        服務狀態詳情（兼容舊系統格式）
    """
    try:
        # 查詢特定服務的 up 指標
        query = f'up{{service="{service_name}"}} or up{{job="{service_name}"}}'
        results = await query_prometheus(query)

        if not results:
            return APIResponse.error(
                message=f"Service '{service_name}' not found in Prometheus",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 取第一個結果（如果有多個實例，取第一個）
        result = results[0]
        metric = result.get("metric", {})
        value = result.get("value", [None, None])[1]

        if value is None:
            return APIResponse.error(
                message=f"Service '{service_name}' has no status data",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            up_value = float(value)
        except (ValueError, TypeError):
            return APIResponse.error(
                message=f"Invalid status value for service '{service_name}'",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 提取 job 和 instance
        job_name = metric.get("job", "unknown")
        instance = metric.get("instance", "unknown")

        # 映射為服務狀態
        service_status = _map_prometheus_to_service_status(job_name, instance, up_value, metric)

        return APIResponse.success(
            data=service_status,
            message="Service status retrieved successfully from Prometheus",
        )

    except Exception as e:
        logger.error(
            f"Failed to get service status from Prometheus: service_name={service_name}, error={str(e)}",
            exc_info=True,
        )
        return APIResponse.error(
            message=f"Failed to get service status from Prometheus: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
