# 代碼功能說明: Task Analyzer API 路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Task Analyzer API 路由"""

from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from services.api.core.response import APIResponse
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest

router = APIRouter()

# 初始化 Task Analyzer
task_analyzer = TaskAnalyzer()


class TaskAnalysisAPIRequest(BaseModel):
    """任務分析 API 請求模型"""

    task: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@router.post("/task-analyzer/analyze", status_code=status.HTTP_200_OK)
async def analyze_task(request: TaskAnalysisAPIRequest) -> JSONResponse:
    """
    分析任務

    Args:
        request: 任務分析請求

    Returns:
        任務分析結果
    """
    try:
        # 構建 TaskAnalysisRequest
        analysis_request = TaskAnalysisRequest(
            task=request.task,
            context=request.context,
            user_id=request.user_id,
            session_id=request.session_id,
        )

        # 執行分析
        result = task_analyzer.analyze(analysis_request)

        return APIResponse.success(
            data=result.model_dump(mode="json"),
            message="Task analysis completed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task analysis failed: {str(e)}",
        )


@router.get("/task-analyzer/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Task Analyzer 健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "task_analyzer"},
        message="Task Analyzer is healthy",
    )
