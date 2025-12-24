# 代碼功能說明: AI治理報告API路由
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""AI治理報告API路由 - 提供AI治理報告生成接口"""

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.services.governance_report_service import get_governance_report_service
from system.security.dependencies import get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/governance", tags=["AI Governance"])


@router.get("/report")
async def get_governance_report(
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    user_id: Optional[str] = Query(None, description="用戶ID（僅管理員可用）"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取AI治理報告

    Args:
        start_time: 開始時間
        end_time: 結束時間
        user_id: 用戶ID（僅管理員可用）
        current_user: 當前認證用戶

    Returns:
        AI治理報告
    """
    try:
        # 非管理員用戶只能查詢自己的報告
        from system.security.models import Permission

        if not current_user.has_permission(Permission.ALL.value):
            user_id = current_user.user_id

        service = get_governance_report_service()
        report = service.generate_report(start_time=start_time, end_time=end_time, user_id=user_id)

        return APIResponse.success(
            data=report,
            message="AI治理報告生成成功",
        )
    except Exception as e:
        logger.error("AI治理報告生成失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"AI治理報告生成失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
