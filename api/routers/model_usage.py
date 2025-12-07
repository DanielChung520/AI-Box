# 代碼功能說明: 模型使用統計API路由
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""模型使用統計API路由 - 提供模型使用追蹤和統計查詢接口"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Query, Depends, status, HTTPException
from fastapi.responses import JSONResponse
import structlog
from functools import partial

from api.core.response import APIResponse
from services.api.models.model_usage import (
    ModelUsage,
    ModelUsageQuery,
    ModelUsageStats,
    ModelPurpose,
)
from services.api.services.model_usage_service import get_model_usage_service
from system.security.dependencies import get_current_user, require_permission
from system.security.models import User, Permission

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/model-usage", tags=["Model Usage"])


@router.get("/records")
async def list_model_usage_records(
    model_name: Optional[str] = Query(None, description="模型名稱"),
    user_id: Optional[str] = Query(None, description="用戶ID"),
    file_id: Optional[str] = Query(None, description="文件ID"),
    task_id: Optional[str] = Query(None, description="任務ID"),
    purpose: Optional[str] = Query(None, description="使用目的"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    查詢模型使用記錄

    Args:
        model_name: 模型名稱
        user_id: 用戶ID
        file_id: 文件ID
        task_id: 任務ID
        purpose: 使用目的
        start_time: 開始時間
        end_time: 結束時間
        limit: 返回數量限制
        offset: 偏移量
        current_user: 當前認證用戶

    Returns:
        模型使用記錄列表
    """
    try:
        # 非管理員用戶只能查詢自己的記錄
        if not current_user.has_permission(Permission.ALL.value):
            user_id = current_user.user_id

        # 解析使用目的
        purpose_enum = None
        if purpose:
            try:
                purpose_enum = ModelPurpose(purpose.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid purpose: {purpose}",
                )

        query_params = ModelUsageQuery(
            model_name=model_name,
            user_id=user_id,
            file_id=file_id,
            task_id=task_id,
            purpose=purpose_enum,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

        service = get_model_usage_service()
        records = service.query(query_params)

        return APIResponse.success(
            data={
                "records": [record.model_dump(mode="json") for record in records],
                "total": len(records),
            },
            message="模型使用記錄查詢成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("模型使用記錄查詢失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"模型使用記錄查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/stats")
async def get_model_usage_stats(
    model_name: Optional[str] = Query(None, description="模型名稱"),
    user_id: Optional[str] = Query(None, description="用戶ID"),
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取模型使用統計

    Args:
        model_name: 模型名稱（可選）
        user_id: 用戶ID（可選）
        start_time: 開始時間（可選）
        end_time: 結束時間（可選）
        current_user: 當前認證用戶

    Returns:
        模型使用統計列表
    """
    try:
        # 非管理員用戶只能查詢自己的統計
        if not current_user.has_permission(Permission.ALL.value):
            user_id = current_user.user_id

        service = get_model_usage_service()
        stats = service.get_stats(
            model_name=model_name,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
        )

        return APIResponse.success(
            data={"stats": [stat.model_dump(mode="json") for stat in stats]},
            message="模型使用統計查詢成功",
        )
    except Exception as e:
        logger.error("模型使用統計查詢失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"模型使用統計查詢失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
