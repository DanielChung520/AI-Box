# 代碼功能說明: 數據質量API路由
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""數據質量API路由 - 提供數據質量檢查和報告接口"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
import structlog

from api.core.response import APIResponse
from services.api.services.data_quality_service import get_data_quality_service
from system.security.dependencies import get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/check/{file_id}")
async def check_file_quality(
    file_id: str,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    檢查文件質量

    Args:
        file_id: 文件ID
        current_user: 當前認證用戶

    Returns:
        質量檢查結果
    """
    try:
        service = get_data_quality_service()
        result = service.check_file_quality(file_id)

        return APIResponse.success(
            data=result,
            message="文件質量檢查完成",
        )
    except Exception as e:
        logger.error("文件質量檢查失敗", file_id=file_id, error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"文件質量檢查失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
