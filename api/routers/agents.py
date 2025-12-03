# 代碼功能說明: Agent 相關路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Agent 相關 API 路由"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, status, Depends, HTTPException
from pydantic import BaseModel

from api.core.response import APIResponse
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()


class AgentExecuteRequest(BaseModel):
    """Agent 執行請求模型"""

    agent_id: str
    task: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None


class AgentExecuteResponse(BaseModel):
    """Agent 執行響應模型"""

    agent_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.post("/agents/execute", status_code=status.HTTP_200_OK)
async def execute_agent(
    request: AgentExecuteRequest,
    user: User = Depends(get_current_user),
):
    """
    執行 Agent 任務

    支持內部 Agent（直接調用）和外部 Agent（通過 HTTP/MCP 調用）的統一執行接口。
    Registry 會自動根據 Agent 的 is_internal 標識選擇合適的調用方式。

    Args:
        request: Agent 執行請求
            - agent_id: Agent ID
            - task: 任務數據（Dict）
            - context: 上下文數據（可選）
        user: 當前認證用戶（開發模式下自動提供）

    Returns:
        Agent 執行結果

    注意：此端點使用了認證依賴。在開發模式下（SECURITY_ENABLED=false），
    會自動使用開發用戶，無需提供認證信息。
    """
    try:
        from agents.services.registry.registry import get_agent_registry
        from agents.services.protocol.base import AgentServiceRequest

        registry = get_agent_registry()

        # 獲取 Agent（Registry 會自動返回實例或 Client）
        agent = registry.get_agent(request.agent_id)

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {request.agent_id}",
            )

        # 構建 AgentServiceRequest
        service_request = AgentServiceRequest(
            task_id=f"task_{request.agent_id}_{id(request)}",
            task_type=request.task.get("type", "execute"),
            task_data=request.task,
            context=request.context or {},
            metadata={"requested_by": user.user_id},
        )

        # 執行任務（內部 Agent 直接調用，外部 Agent 通過 Client 調用）
        response = await agent.execute(service_request)

        return APIResponse.success(
            data={
                "agent_id": request.agent_id,
                "task_id": response.task_id,
                "status": response.status,
                "result": response.result,
                "error": response.error,
                "metadata": response.metadata,
            },
            message="Agent execution completed",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        )


@router.get("/agents/discover", status_code=status.HTTP_200_OK)
async def discover_agents(
    capabilities: Optional[List[str]] = None,
    agent_type: Optional[str] = None,
    is_internal: Optional[bool] = None,
):
    """
    發現可用的 Agent

    支持按能力、類型、內部/外部標識過濾 Agent。

    Args:
        capabilities: 需要的能力列表（可選）
        agent_type: Agent 類型過濾器（可選）
        is_internal: 是否只返回內部 Agent（可選，None 表示返回所有）

    Returns:
        可用 Agent 列表（包含 is_internal 標識）
    """
    try:
        from agents.services.registry.discovery import AgentDiscovery
        from agents.services.registry.registry import get_agent_registry
        from agents.services.registry.models import AgentStatus

        registry = get_agent_registry()
        discovery = AgentDiscovery(registry=registry)

        # 發現 Agent
        agents = discovery.discover_agents(
            required_capabilities=capabilities,
            agent_type=agent_type,
            status=AgentStatus.ONLINE,
        )

        # 過濾內部/外部 Agent
        if is_internal is not None:
            agents = [
                agent for agent in agents if agent.endpoints.is_internal == is_internal
            ]

        # 構建響應數據
        agents_data = []
        for agent in agents:
            agent_dict = agent.model_dump(mode="json")
            agent_dict["is_internal"] = agent.endpoints.is_internal
            agent_dict["protocol"] = (
                agent.endpoints.protocol.value if agent.endpoints.protocol else None
            )
            agents_data.append(agent_dict)

        return APIResponse.success(
            data={"agents": agents_data, "count": len(agents_data)},
            message="Agent discovery completed",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent discovery failed: {str(e)}",
        )


@router.get("/agents/{agent_id}/status", status_code=status.HTTP_200_OK)
async def get_agent_status(agent_id: str):
    """
    獲取 Agent 狀態

    Args:
        agent_id: Agent ID

    Returns:
        Agent 狀態信息
    """
    # TODO: 實現 Agent 狀態查詢邏輯
    return APIResponse.success(
        data={
            "agent_id": agent_id,
            "status": "unknown",
        },
        message="Agent status retrieved",
    )
