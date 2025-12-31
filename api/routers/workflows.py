# 代碼功能說明: 工作流 API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""工作流執行 API 路由（LangChain、AutoGen、混合模式）"""

import logging
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agents.task_analyzer.models import WorkflowType
from agents.workflows.base import WorkflowRequestContext
from agents.workflows.factory_router import get_workflow_factory_router
from api.core.response import APIResponse

logger = logging.getLogger(__name__)

router = APIRouter()


class WorkflowExecuteRequest(BaseModel):
    """工作流執行請求模型"""

    task: str = Field(..., description="任務描述")
    workflow_type: Optional[str] = Field(default="langchain", description="工作流類型")
    user_id: Optional[str] = Field(default=None, description="用戶ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    workflow_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="工作流配置"
    )


class HybridWorkflowExecuteRequest(BaseModel):
    """混合模式工作流執行請求模型"""

    task: str = Field(..., description="任務描述")
    primary_mode: Literal["autogen", "langgraph", "crewai"] = Field(
        default="autogen", description="主要模式"
    )
    fallback_modes: Optional[List[Literal["autogen", "langgraph", "crewai"]]] = Field(
        default=None, description="備用模式列表"
    )
    user_id: Optional[str] = Field(default=None, description="用戶ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    workflow_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="工作流配置"
    )


class AutoGenPlanRequest(BaseModel):
    """AutoGen 規劃請求模型"""

    task: str = Field(..., description="任務描述")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    user_id: Optional[str] = Field(default=None, description="用戶ID")
    max_steps: Optional[int] = Field(default=10, description="最大步驟數")
    workflow_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="工作流配置"
    )


@router.post("/workflows/langchain/execute", status_code=status.HTTP_200_OK)
async def execute_langchain_workflow(request: WorkflowExecuteRequest) -> JSONResponse:
    """
    執行 LangChain/Graph 工作流

    Args:
        request: 工作流執行請求

    Returns:
        執行結果
    """
    try:
        # 生成任務ID
        task_id = str(uuid.uuid4())

        # 構建請求上下文
        request_ctx = WorkflowRequestContext(
            task_id=task_id,
            task=request.task,
            user_id=request.user_id,
            context=request.context,
            workflow_config=request.workflow_config,
        )

        # 獲取工作流工廠路由器
        router_instance = get_workflow_factory_router()

        # 構建工作流
        logger.info(f"Building LangChain workflow for task: {task_id}")
        workflow = router_instance.build_workflow(WorkflowType.LANGCHAIN, request_ctx)
        if not workflow:
            error_msg = "Failed to build LangChain workflow: factory returned None"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

        # 執行工作流
        logger.info(f"Executing LangChain workflow for task: {task_id}")
        result = await workflow.run()

        # 返回結果
        logger.info(f"LangChain workflow completed for task: {task_id}, status: {result.status}")
        return APIResponse.success(
            data={
                "task_id": task_id,
                "status": result.status,
                "output": result.output,
                "reasoning": result.reasoning,
                "telemetry": [{"name": e.name, "payload": e.payload} for e in result.telemetry],
                "state_snapshot": result.state_snapshot,
            },
            message="LangChain workflow executed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"LangChain workflow execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


@router.post("/workflows/autogen/plan", status_code=status.HTTP_200_OK)
async def autogen_plan(request: AutoGenPlanRequest) -> JSONResponse:
    """
    AutoGen 自動規劃

    Args:
        request: 規劃請求

    Returns:
        規劃結果
    """
    try:
        # 生成任務ID
        task_id = str(uuid.uuid4())

        # 構建請求上下文
        request_ctx = WorkflowRequestContext(
            task_id=task_id,
            task=request.task,
            user_id=request.user_id,
            context=request.context,
            workflow_config={
                **(request.workflow_config or {}),
                "max_steps": request.max_steps,
            },
        )

        # 獲取工作流工廠路由器
        router_instance = get_workflow_factory_router()

        # 構建工作流
        workflow = router_instance.build_workflow(WorkflowType.AUTOGEN, request_ctx)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build AutoGen workflow",
            )

        # 執行工作流
        result = await workflow.run()

        # 返回結果
        return APIResponse.success(
            data={
                "task_id": task_id,
                "status": result.status,
                "output": result.output,
                "reasoning": result.reasoning,
                "telemetry": [{"name": e.name, "payload": e.payload} for e in result.telemetry],
                "state_snapshot": result.state_snapshot,
            },
            message="AutoGen planning completed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AutoGen planning failed: {str(e)}",
        ) from e


@router.post("/workflows/hybrid/execute", status_code=status.HTTP_200_OK)
async def execute_hybrid_workflow(
    request: HybridWorkflowExecuteRequest,
) -> JSONResponse:
    """
    執行混合模式工作流（AutoGen + LangGraph）

    Args:
        request: 混合模式工作流執行請求

    Returns:
        執行結果
    """
    try:
        # 生成任務ID
        task_id = str(uuid.uuid4())

        # 構建請求上下文
        request_ctx = WorkflowRequestContext(
            task_id=task_id,
            task=request.task,
            user_id=request.user_id,
            context=request.context,
            workflow_config={
                **(request.workflow_config or {}),
                "primary_mode": request.primary_mode,
                "fallback_modes": request.fallback_modes or ["langgraph"],
            },
        )

        # 獲取工作流工廠路由器
        router_instance = get_workflow_factory_router()

        # 構建混合模式工作流
        workflow = router_instance.build_workflow(WorkflowType.HYBRID, request_ctx)
        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build hybrid workflow",
            )

        # 執行工作流
        result = await workflow.run()

        # 返回結果
        return APIResponse.success(
            data={
                "task_id": task_id,
                "status": result.status,
                "output": result.output,
                "reasoning": result.reasoning,
                "telemetry": [{"name": e.name, "payload": e.payload} for e in result.telemetry],
                "state_snapshot": result.state_snapshot,
            },
            message="Hybrid workflow executed successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid workflow execution failed: {str(e)}",
        ) from e


@router.get("/workflows/health", status_code=status.HTTP_200_OK)
async def workflows_health_check() -> JSONResponse:
    """
    工作流服務健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "workflows"},
        message="Workflow service is healthy",
    )
