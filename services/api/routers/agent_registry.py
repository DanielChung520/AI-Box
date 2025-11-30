# 代碼功能說明: Agent Registry API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry API 路由 - 提供 Agent 註冊和管理接口"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from services.api.core.response import APIResponse
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentStatus,
)
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()


@router.post("/agents/register", status_code=http_status.HTTP_201_CREATED)
async def register_agent(
    request: AgentRegistrationRequest,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    註冊 Agent

    Args:
        request: Agent 註冊請求
        user: 當前認證用戶（可選）

    Returns:
        註冊結果
    """
    try:
        registry = get_agent_registry()
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent registration failed: {str(e)}",
        )


@router.get("/agents/{agent_id}", status_code=http_status.HTTP_200_OK)
async def get_agent(
    agent_id: str,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取 Agent 詳情

    Args:
        agent_id: Agent ID
        user: 當前認證用戶（可選）

    Returns:
        Agent 詳情
    """
    try:
        registry = get_agent_registry()
        agent = registry.get_agent(agent_id)

        if agent:
            return APIResponse.success(
                data=agent.model_dump(mode="json"),
                message="Agent retrieved successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}",
        )


@router.delete("/agents/{agent_id}", status_code=http_status.HTTP_200_OK)
async def unregister_agent(
    agent_id: str,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    取消註冊 Agent

    Args:
        agent_id: Agent ID
        user: 當前認證用戶（可選）

    Returns:
        取消註冊結果
    """
    try:
        registry = get_agent_registry()
        success = registry.unregister_agent(agent_id)

        if success:
            return APIResponse.success(
                data={"agent_id": agent_id},
                message="Agent unregistered successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister agent: {str(e)}",
        )


@router.put("/agents/{agent_id}/status", status_code=http_status.HTTP_200_OK)
async def update_agent_status(
    agent_id: str,
    status: AgentStatus,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    更新 Agent 狀態

    Args:
        agent_id: Agent ID
        status: 新狀態
        user: 當前認證用戶（可選）

    Returns:
        更新結果
    """
    try:
        registry = get_agent_registry()
        success = registry.update_agent_status(agent_id, status)

        if success:
            return APIResponse.success(
                data={"agent_id": agent_id, "status": status.value},
                message="Agent status updated successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent status: {str(e)}",
        )


@router.post("/agents/{agent_id}/heartbeat", status_code=http_status.HTTP_200_OK)
async def update_heartbeat(
    agent_id: str,
) -> JSONResponse:
    """
    更新 Agent 心跳（用於健康檢查）

    Args:
        agent_id: Agent ID

    Returns:
        更新結果
    """
    try:
        registry = get_agent_registry()
        success = registry.update_heartbeat(agent_id)

        if success:
            return APIResponse.success(
                data={"agent_id": agent_id},
                message="Heartbeat updated successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update heartbeat: {str(e)}",
        )
