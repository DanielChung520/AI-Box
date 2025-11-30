# 代碼功能說明: Review Agent API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Review Agent API 路由"""

from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from api.core.response import APIResponse
from agents.core.review.agent import ReviewAgent
from agents.core.review.models import ReviewRequest

router = APIRouter()

# 初始化 Review Agent
review_agent = ReviewAgent()


class ReviewAPIRequest(BaseModel):
    """審查 API 請求模型"""

    result: Dict[str, Any]
    expected: Optional[Dict[str, Any]] = None
    criteria: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/agents/review/validate", status_code=status.HTTP_200_OK)
async def validate_result(request: ReviewAPIRequest) -> JSONResponse:
    """
    驗證執行結果

    Args:
        request: 審查請求

    Returns:
        審查結果
    """
    try:
        # 構建 ReviewRequest
        review_request = ReviewRequest(
            result=request.result,
            expected=request.expected,
            criteria=request.criteria,
            context=request.context,
            metadata=request.metadata or {},
        )

        # 執行審查
        result = review_agent.review(review_request)

        return APIResponse.success(
            data=result.model_dump(mode="json"),
            message="Review completed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review failed: {str(e)}",
        )


@router.get("/agents/review/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Review Agent 健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "review_agent"},
        message="Review Agent is healthy",
    )
