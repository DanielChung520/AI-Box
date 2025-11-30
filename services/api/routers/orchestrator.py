# 代碼功能說明: Agent Orchestrator API 路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Agent Orchestrator API 路由"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.api.core.response import APIResponse
from agents.orchestrator.orchestrator import AgentOrchestrator
from agents.orchestrator.models import (
    AgentRegistrationRequest,
    AgentStatus,
)

router = APIRouter()

# 初始化 Agent Orchestrator
orchestrator = AgentOrchestrator()


class SubmitTaskRequest(BaseModel):
    """提交任務請求模型"""

    task_type: str
    task_data: Dict[str, Any]
    required_agents: Optional[List[str]] = None
    priority: int = 0
    timeout: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class AggregateResultsRequest(BaseModel):
    """聚合結果請求模型"""

    task_ids: List[str]


@router.post("/orchestrator/agents/register", status_code=http_status.HTTP_200_OK)
async def register_agent(request: AgentRegistrationRequest) -> JSONResponse:
    """
    註冊 Agent

    Args:
        request: Agent 註冊請求

    Returns:
        註冊結果
    """
    try:
        success = orchestrator.register_agent(
            agent_id=request.agent_id,
            agent_type=request.agent_type,
            capabilities=request.capabilities,
            metadata=request.metadata,
        )

        if success:
            return APIResponse.success(
                data={"agent_id": request.agent_id},
                message="Agent registered successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Failed to register agent",
            )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent registration failed: {str(e)}",
        )


@router.get("/orchestrator/agents", status_code=http_status.HTTP_200_OK)
async def list_agents(
    agent_type: Optional[str] = None,
    status: Optional[AgentStatus] = None,
) -> JSONResponse:
    """
    列出 Agent

    Args:
        agent_type: Agent 類型過濾器
        status: Agent 狀態過濾器

    Returns:
        Agent 列表
    """
    try:
        agents = orchestrator.list_agents(
            agent_type=agent_type,
            status=status,
        )

        return APIResponse.success(
            data={"agents": [agent.model_dump(mode="json") for agent in agents]},
            message="Agents retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}",
        )


@router.get("/orchestrator/agents/discover", status_code=http_status.HTTP_200_OK)
async def discover_agents(
    required_capabilities: Optional[List[str]] = None,
    agent_type: Optional[str] = None,
) -> JSONResponse:
    """
    發現可用的 Agent

    Args:
        required_capabilities: 需要的能力列表
        agent_type: Agent 類型過濾器

    Returns:
        匹配的 Agent 列表
    """
    try:
        agents = orchestrator.discover_agents(
            required_capabilities=required_capabilities,
            agent_type=agent_type,
        )

        return APIResponse.success(
            data={"agents": [agent.model_dump(mode="json") for agent in agents]},
            message="Agents discovered successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover agents: {str(e)}",
        )


@router.post("/orchestrator/tasks/submit", status_code=http_status.HTTP_200_OK)
async def submit_task(request: SubmitTaskRequest) -> JSONResponse:
    """
    提交任務

    Args:
        request: 任務提交請求

    Returns:
        任務ID
    """
    try:
        task_id = orchestrator.submit_task(
            task_type=request.task_type,
            task_data=request.task_data,
            required_agents=request.required_agents,
            priority=request.priority,
            timeout=request.timeout,
            metadata=request.metadata,
        )

        return APIResponse.success(
            data={"task_id": task_id},
            message="Task submitted successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task submission failed: {str(e)}",
        )


@router.get("/orchestrator/tasks/{task_id}/result", status_code=http_status.HTTP_200_OK)
async def get_task_result(task_id: str) -> JSONResponse:
    """
    獲取任務結果

    Args:
        task_id: 任務ID

    Returns:
        任務結果
    """
    try:
        result = orchestrator.get_task_result(task_id)

        if result:
            return APIResponse.success(
                data=result.model_dump(mode="json"),
                message="Task result retrieved successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Task result not found: {task_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task result: {str(e)}",
        )


@router.post("/orchestrator/tasks/aggregate", status_code=http_status.HTTP_200_OK)
async def aggregate_results(request: AggregateResultsRequest) -> JSONResponse:
    """
    聚合任務結果

    Args:
        request: 聚合結果請求

    Returns:
        聚合結果
    """
    try:
        aggregated = orchestrator.aggregate_results(request.task_ids)

        return APIResponse.success(
            data=aggregated,
            message="Results aggregated successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate results: {str(e)}",
        )


@router.get("/orchestrator/health", status_code=http_status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Agent Orchestrator 健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={
            "status": "healthy",
            "service": "agent_orchestrator",
            "agent_count": len(orchestrator.list_agents()),
        },
        message="Agent Orchestrator is healthy",
    )
