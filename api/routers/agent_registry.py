# 代碼功能說明: Agent Registry API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Registry API 路由 - 提供 Agent 註冊和管理接口"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.models import (
    AgentRegistrationRequest,
    AgentStatus,
    AgentPermissionConfig,
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

    支持內部 Agent（is_internal=True）和外部 Agent（is_internal=False）註冊。
    外部 Agent 需要提供認證配置（API Key、mTLS 證書等）。

    Args:
        request: Agent 註冊請求
            - endpoints.is_internal: 是否為內部 Agent
            - permissions: 權限配置（外部 Agent 需要認證配置）
        user: 當前認證用戶（可選）

    Returns:
        註冊結果
    """
    try:
        registry = get_agent_registry()

        # 對於外部 Agent，驗證認證配置
        if not request.endpoints.is_internal:
            permissions = request.permissions or AgentPermissionConfig()

            # Phase 1: 外部 Agent 必須提供 Secret ID（強制要求）
            if not permissions.secret_id:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="External agent must provide Secret ID for authentication. Please verify your Secret ID/Key first.",
                )

            # 驗證 Secret ID 是否有效
            from agents.services.auth.secret_manager import get_secret_manager

            secret_manager = get_secret_manager()

            # 檢查 Secret ID 是否存在
            secret_info = secret_manager.get_secret_info(permissions.secret_id)
            if not secret_info:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid Secret ID: '{permissions.secret_id}'. Please verify your Secret ID/Key first.",
                )

            # 驗證 Secret ID 是否已綁定到其他 Agent
            if secret_manager.is_secret_bound(permissions.secret_id):
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"Secret ID '{permissions.secret_id}' is already bound to another agent",
                )

            # 注意：Secret Key 應該在註冊前通過 /agents/secrets/verify 端點驗證
            # 這裡我們只檢查 Secret ID 是否存在和未綁定

            # 外部 Agent 可以同時提供其他認證方式（作為補充安全措施）
            # 但 Secret ID 是必需的

        # 註冊 Agent（內部 Agent 不需要 instance，外部 Agent 通過 HTTP/MCP 調用）
        success = registry.register_agent(request, instance=None)

        if success:
            # 如果是外部 Agent 且提供了 Secret ID，綁定 Secret ID 到 Agent ID
            if (
                not request.endpoints.is_internal
                and request.permissions
                and request.permissions.secret_id
            ):
                from agents.services.auth.secret_manager import get_secret_manager

                secret_manager = get_secret_manager()
                bind_success = secret_manager.bind_secret_to_agent(
                    request.permissions.secret_id, request.agent_id
                )
                if not bind_success:
                    # 註冊成功但綁定失敗，記錄警告但不影響註冊
                    import logging

                    logging.warning(
                        f"Failed to bind secret '{request.permissions.secret_id}' to agent '{request.agent_id}'"
                    )

            return APIResponse.success(
                data={
                    "agent_id": request.agent_id,
                    "status": "registering",
                    "is_internal": request.endpoints.is_internal,
                    "protocol": request.endpoints.protocol.value
                    if request.endpoints.protocol
                    else None,
                    "secret_id": request.permissions.secret_id
                    if request.permissions
                    else None,
                },
                message="Agent registered successfully. Waiting for admin approval.",
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

    返回 Agent 的完整信息，包括：
    - 基本信息（ID、名稱、類型等）
    - 端點配置（HTTP/MCP、協議類型、是否內部）
    - 權限配置（資源訪問權限、認證配置）
    - 狀態信息

    Args:
        agent_id: Agent ID
        user: 當前認證用戶（可選）

    Returns:
        Agent 詳情（包含 is_internal 和認證配置信息）
    """
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_id)

        if agent_info:
            # 構建響應數據，包含內部/外部標識
            agent_data = agent_info.model_dump(mode="json")
            agent_data["is_internal"] = agent_info.endpoints.is_internal
            agent_data["protocol"] = (
                agent_info.endpoints.protocol.value
                if agent_info.endpoints.protocol
                else None
            )

            return APIResponse.success(
                data=agent_data,
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


@router.post("/agents/{agent_id}/approve", status_code=http_status.HTTP_200_OK)
async def approve_agent(
    agent_id: str,
    approved: bool = True,
    comment: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    管理員核准或拒絕 Agent 註冊申請

    只有管理員可以將 Agent 從「註冊中」狀態轉為「在線」或「已作廢」狀態。

    Args:
        agent_id: Agent ID
        approved: 是否核准（True=核准轉為在線，False=拒絕轉為已作廢）
        comment: 核准/拒絕備註
        user: 當前認證用戶（必須是管理員）

    Returns:
        核准結果
    """
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_id)

        if not agent_info:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}",
            )

        # 檢查當前狀態是否為「註冊中」
        if agent_info.status != AgentStatus.REGISTERING:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Agent is not in 'registering' status. Current status: {agent_info.status.value}",
            )

        # TODO: 檢查用戶是否為管理員
        # 暫時允許所有已認證用戶執行，後續需要添加權限檢查
        # if user and not user.has_permission("agent:approve"):
        #     raise HTTPException(
        #         status_code=http_status.HTTP_403_FORBIDDEN,
        #         detail="Only admins can approve agent registrations",
        #     )

        # 根據核准結果更新狀態
        new_status = AgentStatus.ONLINE if approved else AgentStatus.DEPRECATED
        success = registry.update_agent_status(agent_id, new_status)

        if success:
            return APIResponse.success(
                data={
                    "agent_id": agent_id,
                    "status": new_status.value,
                    "approved": approved,
                    "comment": comment,
                },
                message=f"Agent {'approved' if approved else 'rejected'} successfully",
            )
        else:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update agent status",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve agent: {str(e)}",
        )


@router.put("/agents/{agent_id}/status", status_code=http_status.HTTP_200_OK)
async def update_agent_status(
    agent_id: str,
    status: AgentStatus,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    更新 Agent 狀態（開發者操作）

    Agent 開發者可以將「在線」狀態的 Agent 轉為「維修中」或「已作廢」。
    其他狀態轉換需要管理員權限。

    Args:
        agent_id: Agent ID
        status: 新狀態
        user: 當前認證用戶（可選）

    Returns:
        更新結果
    """
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_id)

        if not agent_info:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent not found: {agent_id}",
            )

        current_status = agent_info.status

        # 狀態轉換驗證
        # 開發者可以執行的轉換：
        # - ONLINE -> MAINTENANCE
        # - ONLINE -> DEPRECATED
        # - MAINTENANCE -> DEPRECATED
        developer_allowed_transitions = [
            (AgentStatus.ONLINE, AgentStatus.MAINTENANCE),
            (AgentStatus.ONLINE, AgentStatus.DEPRECATED),
            (AgentStatus.MAINTENANCE, AgentStatus.DEPRECATED),
        ]

        is_developer_transition = (
            current_status,
            status,
        ) in developer_allowed_transitions
        is_same_status = current_status == status

        if not is_same_status and not is_developer_transition:
            # 其他轉換需要管理員權限（暫時允許，後續需要添加權限檢查）
            # TODO: 添加管理員權限檢查
            pass

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
