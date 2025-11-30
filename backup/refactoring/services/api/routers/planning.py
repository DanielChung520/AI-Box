# 代碼功能說明: Planning Agent API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Planning Agent API 路由"""

from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.api.core.response import APIResponse
from agents.core.planning.agent import PlanningAgent
from agents.core.planning.models import PlanRequest, PlanStepStatus

router = APIRouter()

# 初始化 Planning Agent
planning_agent = PlanningAgent()


class PlanGenerateRequest(BaseModel):
    """計劃生成 API 請求模型"""

    task: str
    context: Optional[Dict[str, Any]] = None
    requirements: Optional[List[str]] = None
    constraints: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


class PlanStepUpdateRequest(BaseModel):
    """計劃步驟更新請求模型"""

    status: PlanStepStatus
    result: Optional[Dict[str, Any]] = None


@router.post("/agents/planning/generate", status_code=status.HTTP_200_OK)
async def generate_plan(request: PlanGenerateRequest) -> JSONResponse:
    """
    生成任務計劃

    Args:
        request: 計劃生成請求

    Returns:
        計劃結果
    """
    try:
        # 構建 PlanRequest
        plan_request = PlanRequest(
            task=request.task,
            context=request.context,
            requirements=request.requirements,
            constraints=request.constraints,
            metadata=request.metadata or {},
        )

        # 執行計劃生成
        result = planning_agent.generate_plan(plan_request)

        return APIResponse.success(
            data=result.model_dump(mode="json"),
            message="Plan generated successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan generation failed: {str(e)}",
        )


@router.post(
    "/agents/planning/{plan_id}/steps/{step_id}/update",
    status_code=status.HTTP_200_OK,
)
async def update_step_status(
    plan_id: str, step_id: str, request: PlanStepUpdateRequest
) -> JSONResponse:
    """
    更新計劃步驟狀態

    Args:
        plan_id: 計劃ID
        step_id: 步驟ID
        request: 步驟更新請求

    Returns:
        更新結果
    """
    try:
        success = planning_agent.update_step_status(
            plan_id=plan_id,
            step_id=step_id,
            status=request.status,
            result=request.result,
        )

        if success:
            return APIResponse.success(
                data={"plan_id": plan_id, "step_id": step_id, "updated": True},
                message="Step status updated successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan or step not found: plan_id={plan_id}, step_id={step_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update step status: {str(e)}",
        )


@router.get("/agents/planning/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Planning Agent 健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "planning_agent"},
        message="Planning Agent is healthy",
    )
