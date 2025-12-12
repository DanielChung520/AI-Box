# 代碼功能說明: CrewAI Task 管理 API 路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""CrewAI Task 管理 API 路由"""

from typing import Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.api.core.response import APIResponse
from agents.crewai.task_registry import TaskRegistry
from agents.crewai.task_scheduler import TaskScheduler
from agents.crewai.task_models import (
    CrewTask,
    TaskStatus,
    TaskPriority,
)

router = APIRouter()

# 初始化 Task Registry 和 Scheduler
task_registry = TaskRegistry()
task_scheduler = TaskScheduler(task_registry)


class CreateTaskRequest(BaseModel):
    """創建任務請求模型"""

    crew_id: str = Field(..., description="隊伍 ID")
    description: str = Field(..., description="任務描述")
    assigned_agent: Optional[str] = Field(default=None, description="分配的 Agent 角色")
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM, description="任務優先級"
    )
    metadata: Optional[Dict] = Field(default_factory=dict, description="元數據")


class UpdateTaskStatusRequest(BaseModel):
    """更新任務狀態請求模型"""

    status: TaskStatus = Field(..., description="新狀態")
    message: Optional[str] = Field(default=None, description="狀態更新消息")
    metadata: Optional[Dict] = Field(default=None, description="元數據")


@router.post("/api/v1/crewai/tasks", status_code=http_status.HTTP_201_CREATED)
async def create_task(request: CreateTaskRequest) -> JSONResponse:
    """
    創建任務

    Args:
        request: 創建任務請求

    Returns:
        創建的任務
    """
    try:
        import uuid

        task = CrewTask(
            task_id=str(uuid.uuid4()),
            crew_id=request.crew_id,
            description=request.description,
            assigned_agent=request.assigned_agent,
            priority=request.priority,
            metadata=request.metadata,
        )

        # 註冊並排程任務
        if not task_registry.register_task(task):
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to register task",
            )

        if not task_scheduler.schedule_task(task):
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to schedule task",
            )

        return APIResponse.success(
            data=task.model_dump(),
            message="Task created successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(exc)}",
        ) from exc


@router.get("/api/v1/crewai/tasks", status_code=http_status.HTTP_200_OK)
async def list_tasks(
    crew_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
) -> JSONResponse:
    """
    列出任務

    Args:
        crew_id: 隊伍 ID 過濾器（可選）
        status: 狀態過濾器（可選）

    Returns:
        任務列表
    """
    try:
        tasks = task_registry.list_tasks(crew_id=crew_id, status=status)
        return APIResponse.success(
            data=[task.model_dump(mode="json") for task in tasks],
            message="Tasks retrieved successfully",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(exc)}",
        ) from exc


@router.get("/api/v1/crewai/tasks/{task_id}", status_code=http_status.HTTP_200_OK)
async def get_task(task_id: str) -> JSONResponse:
    """
    獲取任務詳情

    Args:
        task_id: 任務 ID

    Returns:
        任務詳情
    """
    try:
        task = task_registry.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        return APIResponse.success(
            data=task.model_dump(mode="json"),
            message="Task retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task: {str(exc)}",
        ) from exc


@router.put(
    "/api/v1/crewai/tasks/{task_id}/status",
    status_code=http_status.HTTP_200_OK,
)
async def update_task_status(
    task_id: str,
    request: UpdateTaskStatusRequest,
) -> JSONResponse:
    """
    更新任務狀態

    Args:
        task_id: 任務 ID
        request: 更新任務狀態請求

    Returns:
        更新結果
    """
    try:
        success = task_registry.update_task_status(
            task_id,
            request.status,
            message=request.message,
            metadata=request.metadata,
        )

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found",
            )

        task = task_registry.get_task(task_id)
        return APIResponse.success(
            data=task.model_dump(mode="json") if task else {},
            message="Task status updated successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task status: {str(exc)}",
        ) from exc


@router.get(
    "/api/v1/crewai/tasks/{task_id}/history",
    status_code=http_status.HTTP_200_OK,
)
async def get_task_history(task_id: str) -> JSONResponse:
    """
    獲取任務歷史

    Args:
        task_id: 任務 ID

    Returns:
        任務歷史
    """
    try:
        history = task_registry.get_task_history(task_id)
        if not history:
            # 檢查任務是否存在
            task = task_registry.get_task(task_id)
            if not task:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Task '{task_id}' not found",
                )

        return APIResponse.success(
            data=[entry.to_dict() for entry in history],
            message="Task history retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task history: {str(exc)}",
        ) from exc


@router.get(
    "/api/v1/crewai/tasks/{task_id}/result",
    status_code=http_status.HTTP_200_OK,
)
async def get_task_result(task_id: str) -> JSONResponse:
    """
    獲取任務執行結果

    Args:
        task_id: 任務 ID

    Returns:
        任務結果
    """
    try:
        result = task_registry.get_task_result(task_id)
        if not result:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Task result '{task_id}' not found",
            )

        return APIResponse.success(
            data=result.model_dump(mode="json"),
            message="Task result retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task result: {str(exc)}",
        ) from exc
