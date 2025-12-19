# 代碼功能說明: CrewAI API 路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""CrewAI Crew Manager API 路由"""

import uuid
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agents.crewai.manager import CrewManager
from agents.crewai.models import AgentRole, CollaborationMode, CrewResourceQuota
from agents.task_analyzer.models import WorkflowType
from agents.workflows.base import WorkflowRequestContext
from agents.workflows.factory_router import get_workflow_factory_router
from api.core.response import APIResponse

router = APIRouter()

# 初始化 Crew Manager
crew_manager = CrewManager()


class CreateCrewRequest(BaseModel):
    """創建隊伍請求模型"""

    name: str = Field(..., description="隊伍名稱")
    description: Optional[str] = Field(default=None, description="隊伍描述")
    agents: Optional[List[AgentRole]] = Field(default_factory=list, description="Agent 列表")
    collaboration_mode: CollaborationMode = Field(
        default=CollaborationMode.SEQUENTIAL, description="協作模式"
    )
    resource_quota: Optional[CrewResourceQuota] = Field(default=None, description="資源配額")
    metadata: Optional[Dict] = Field(default_factory=dict, description="元數據")


class UpdateCrewRequest(BaseModel):
    """更新隊伍請求模型"""

    name: Optional[str] = Field(default=None, description="隊伍名稱")
    description: Optional[str] = Field(default=None, description="隊伍描述")
    collaboration_mode: Optional[CollaborationMode] = Field(default=None, description="協作模式")
    resource_quota: Optional[CrewResourceQuota] = Field(default=None, description="資源配額")
    metadata: Optional[Dict] = Field(default=None, description="元數據")


class AddAgentRequest(BaseModel):
    """添加 Agent 請求模型"""

    agent: AgentRole = Field(..., description="Agent 角色")


class ExecuteCrewRequest(BaseModel):
    """執行 Crew 請求模型"""

    inputs: Dict = Field(..., description="輸入數據")
    user_id: Optional[str] = Field(default=None, description="用戶ID")
    context: Optional[Dict] = Field(default_factory=dict, description="上下文信息")


@router.post("/crews", status_code=http_status.HTTP_201_CREATED)
async def create_crew(request: CreateCrewRequest) -> JSONResponse:
    """
    創建隊伍

    Args:
        request: 創建隊伍請求

    Returns:
        創建的隊伍配置
    """
    try:
        config = crew_manager.create_crew(
            name=request.name,
            description=request.description,
            agents=request.agents,
            collaboration_mode=request.collaboration_mode,
            resource_quota=request.resource_quota,
            metadata=request.metadata,
        )
        return APIResponse.success(
            data=config.model_dump(mode="json"),
            message="Crew created successfully",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create crew: {str(exc)}",
        ) from exc


@router.get("/crews", status_code=http_status.HTTP_200_OK)
async def list_crews() -> JSONResponse:
    """
    列出所有隊伍

    Returns:
        隊伍列表
    """
    try:
        crews = crew_manager.list_crews()  # 返回 List[CrewConfig]
        return APIResponse.success(
            data=[crew.dict() for crew in crews],  # crew 是 CrewConfig，直接使用 dict()
            message="Crews retrieved successfully",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list crews: {str(exc)}",
        ) from exc


@router.get("/crews/{crew_id}", status_code=http_status.HTTP_200_OK)
async def get_crew(crew_id: str) -> JSONResponse:
    """
    獲取隊伍詳情

    Args:
        crew_id: 隊伍 ID

    Returns:
        隊伍配置
    """
    try:
        config = crew_manager.get_crew(crew_id)
        if not config:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' not found",
            )

        return APIResponse.success(
            data=config.model_dump(mode="json"),
            message="Crew retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get crew: {str(exc)}",
        ) from exc


@router.put("/crews/{crew_id}", status_code=http_status.HTTP_200_OK)
async def update_crew(crew_id: str, request: UpdateCrewRequest) -> JSONResponse:
    """
    更新隊伍

    Args:
        crew_id: 隊伍 ID
        request: 更新隊伍請求

    Returns:
        更新後的隊伍配置
    """
    try:
        config = crew_manager.get_crew(crew_id)
        if not config:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' not found",
            )

        # 更新配置
        if request.name is not None:
            config.name = request.name
        if request.description is not None:
            config.description = request.description
        if request.collaboration_mode is not None:
            config.collaboration_mode = request.collaboration_mode
        if request.resource_quota is not None:
            config.resource_quota = request.resource_quota
        if request.metadata is not None:
            config.metadata = request.metadata

        return APIResponse.success(
            data=config.model_dump(mode="json"),
            message="Crew updated successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update crew: {str(exc)}",
        ) from exc


@router.delete("/crews/{crew_id}", status_code=http_status.HTTP_200_OK)
async def delete_crew(crew_id: str) -> JSONResponse:
    """
    刪除隊伍

    Args:
        crew_id: 隊伍 ID

    Returns:
        刪除結果
    """
    try:
        success = crew_manager.delete_crew(crew_id)
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' not found",
            )

        return APIResponse.success(
            data={"crew_id": crew_id},
            message="Crew deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete crew: {str(exc)}",
        ) from exc


@router.get("/crews/{crew_id}/metrics", status_code=http_status.HTTP_200_OK)
async def get_crew_metrics(crew_id: str) -> JSONResponse:
    """
    獲取觀測指標

    Args:
        crew_id: 隊伍 ID

    Returns:
        觀測指標
    """
    try:
        metrics = crew_manager.get_metrics(crew_id)
        if not metrics:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' not found",
            )

        return APIResponse.success(
            data=metrics.model_dump(mode="json"),
            message="Metrics retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(exc)}",
        ) from exc


@router.post("/crews/{crew_id}/agents", status_code=http_status.HTTP_200_OK)
async def add_agent_to_crew(crew_id: str, request: AddAgentRequest) -> JSONResponse:
    """
    添加 Agent 到隊伍

    Args:
        crew_id: 隊伍 ID
        request: 添加 Agent 請求

    Returns:
        操作結果
    """
    try:
        success = crew_manager.add_agent(crew_id, request.agent)
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' not found",
            )

        return APIResponse.success(
            data={"crew_id": crew_id, "agent_role": request.agent.role},
            message="Agent added successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add agent: {str(exc)}",
        ) from exc


@router.delete(
    "/crews/{crew_id}/agents/{agent_role}",
    status_code=http_status.HTTP_200_OK,
)
async def remove_agent_from_crew(crew_id: str, agent_role: str) -> JSONResponse:
    """
    從隊伍移除 Agent

    Args:
        crew_id: 隊伍 ID
        agent_role: Agent 角色名稱

    Returns:
        操作結果
    """
    try:
        success = crew_manager.remove_agent(crew_id, agent_role)
        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' or agent '{agent_role}' not found",
            )

        return APIResponse.success(
            data={"crew_id": crew_id, "agent_role": agent_role},
            message="Agent removed successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove agent: {str(exc)}",
        ) from exc


@router.post(
    "/crewai/crews/{crew_id}/execute",
    status_code=http_status.HTTP_200_OK,
)
async def execute_crew(crew_id: str, request: ExecuteCrewRequest) -> JSONResponse:
    """
    執行 Crew

    Args:
        crew_id: 隊伍 ID
        request: 執行請求

    Returns:
        執行結果
    """
    try:
        # 檢查 Crew 是否存在
        config = crew_manager.get_crew(crew_id)
        if not config:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Crew '{crew_id}' not found",
            )

        # 生成任務ID
        task_id = str(uuid.uuid4())

        # 從 inputs 中提取任務描述
        task = request.inputs.get("task", "")

        # 構建請求上下文
        request_ctx = WorkflowRequestContext(
            task_id=task_id,
            task=task,
            user_id=request.user_id,
            context={
                **(request.context or {}),
                "crew_id": crew_id,
                "inputs": request.inputs,
            },
            workflow_config={"crew_id": crew_id},
        )

        # 獲取工作流工廠路由器
        router_instance = get_workflow_factory_router()

        # 構建工作流
        workflow = router_instance.build_workflow(WorkflowType.CREWAI, request_ctx)
        if not workflow:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to build CrewAI workflow",
            )

        # 執行工作流
        result = await workflow.run()

        # 返回結果
        return APIResponse.success(
            data={
                "task_id": task_id,
                "crew_id": crew_id,
                "status": result.status,
                "output": result.output,
                "reasoning": result.reasoning,
                "telemetry": [{"name": e.name, "payload": e.payload} for e in result.telemetry],
                "state_snapshot": result.state_snapshot,
            },
            message="Crew executed successfully",
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute crew: {str(exc)}",
        ) from exc
