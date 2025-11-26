# 代碼功能說明: 健康檢查路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""健康檢查端點"""

from fastapi import APIRouter, status
from api_gateway.core.response import APIResponse

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    健康檢查端點

    Returns:
        健康狀態信息
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "api-gateway"},
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
    return APIResponse.success(
        data={"status": "ready", "service": "api-gateway"},
        message="Service is ready",
    )


@router.get("/metrics", status_code=status.HTTP_200_OK)
async def metrics():
    """
    指標端點（簡化版）

    Returns:
        服務指標信息
    """
    # TODO: 實現實際的指標收集
    return APIResponse.success(
        data={
            "service": "api-gateway",
            "version": "1.0.0",
            "metrics": {
                "requests_total": 0,
                "requests_per_second": 0,
            },
        },
        message="Metrics retrieved",
    )
