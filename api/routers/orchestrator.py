# 代碼功能說明: Agent Orchestrator API 路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Agent Orchestrator API 路由"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.services.orchestrator.models import TaskStatus
from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.services.registry.models import AgentRegistrationRequest, AgentStatus
from agents.services.registry.registry import get_agent_registry
from api.core.response import APIResponse

router = APIRouter()

# 初始化 Agent Orchestrator
orchestrator = AgentOrchestrator()
# 獲取 Agent Registry（用於 Agent 註冊）
registry = get_agent_registry()


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
    註冊 Agent（通過 Registry）

    Args:
        request: Agent 註冊請求

    Returns:
        註冊結果

    注意：Agent 註冊現在由 Registry 統一管理，Orchestrator 不再直接管理 Agent。
    """
    try:
        # 直接使用 Registry 註冊 Agent
        success = registry.register_agent(request)

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


@router.get("/orchestrator/tasks/{task_id}/status", status_code=http_status.HTTP_200_OK)
async def get_task_status(task_id: str) -> JSONResponse:
    """
    查詢任務狀態

    Args:
        task_id: 任務ID

    Returns:
        任務狀態信息
    """
    try:
        task_tracker = orchestrator._task_tracker
        task_record = task_tracker.get_task_status(task_id)

        if not task_record:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {task_id}",
            )

        return APIResponse.success(
            data=task_record.to_dict(),
            message="Task status retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.get("/orchestrator/tasks", status_code=http_status.HTTP_200_OK)
async def list_tasks(
    user_id: Optional[str] = Query(None, description="用戶ID過濾器"),
    status: Optional[str] = Query(None, description="任務狀態過濾器（pending/running/completed/failed）"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
) -> JSONResponse:
    """
    查詢任務列表

    Args:
        user_id: 用戶ID過濾器（可選）
        status: 任務狀態過濾器（可選）
        limit: 返回數量限制（1-1000，默認100）

    Returns:
        任務列表
    """
    try:
        task_tracker = orchestrator._task_tracker

        # 轉換狀態字符串為TaskStatus枚舉
        task_status = None
        if status:
            try:
                task_status = TaskStatus(status.lower())
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid status: {status}. Valid values: pending, running, completed, failed",
                )

        tasks = task_tracker.list_tasks(user_id=user_id, status=task_status, limit=limit)

        return APIResponse.success(
            data={
                "tasks": [task.to_dict() for task in tasks],
                "count": len(tasks),
            },
            message="Tasks retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}",
        )


@router.get("/orchestrator/tasks/user/{user_id}", status_code=http_status.HTTP_200_OK)
async def get_user_tasks(
    user_id: str,
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
) -> JSONResponse:
    """
    查詢用戶的所有任務

    Args:
        user_id: 用戶ID
        limit: 返回數量限制（1-1000，默認100）

    Returns:
        用戶的任務列表
    """
    try:
        task_tracker = orchestrator._task_tracker
        tasks = task_tracker.get_tasks_by_user(user_id, limit=limit)

        return APIResponse.success(
            data={
                "tasks": [task.to_dict() for task in tasks],
                "count": len(tasks),
                "user_id": user_id,
            },
            message="User tasks retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user tasks: {str(e)}",
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
