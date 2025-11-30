# 代碼功能說明: 健康檢查路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""健康檢查端點"""

from fastapi import APIRouter, status
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from api.core.response import APIResponse
from api.core.version import get_version_info

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    健康檢查端點

    Returns:
        健康狀態信息
    """
    version_info = get_version_info()
    return APIResponse.success(
        data={
            "status": "healthy",
            "service": "api",
            "version": version_info["version"],
        },
        message="Service is healthy",
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """
    就緒檢查端點

    Returns:
        就緒狀態信息
    """
    # TODO: 檢查依賴服務狀態（資料庫、Redis 等）
    version_info = get_version_info()
    return APIResponse.success(
        data={
            "status": "ready",
            "service": "api",
            "version": version_info["version"],
        },
        message="Service is ready",
    )


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def metrics():
    """
    Prometheus metrics 端點。
    """
    payload = generate_latest()
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
