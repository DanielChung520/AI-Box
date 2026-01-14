# 代碼功能說明: Agent Registry API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-14 16:05 UTC+8

"""Agent Registry API 路由 - 提供 Agent 註冊和管理接口"""

import json
import os
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from agents.services.registry.models import (
    AgentPermissionConfig,
    AgentRegistrationRequest,
    AgentStatus,
)
from agents.services.registry.registry import get_agent_registry
from api.core.response import APIResponse
from services.api.models.agent_display_config import AgentConfig, MultilingualText
from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()


def _react_icon_to_fa(icon_name: Optional[str]) -> str:
    """將 react-icons 格式（如 FaRobot）轉換為 FontAwesome 格式（如 fa-robot）"""
    if not icon_name:
        return "fa-robot"  # 默認圖標

    if icon_name.startswith("fa-"):
        return icon_name

    # 移除前綴（Fa, Md, Hi 等）
    fa_icon = re.sub(
        r"^(Fa|Md|Hi|Si|Lu|Tb|Ri|Bs|Bi|Ai|Io|Gr|Im|Wi|Di|Fi|Gi|Go|Hi2|Sl|Tb2|Vsc|Cg)", "", icon_name
    )

    # 將駝峰命名轉換為 kebab-case
    fa_icon = re.sub(r"([a-z])([A-Z])", r"\1-\2", fa_icon).lower()

    # 確保以 fa- 開頭
    if not fa_icon.startswith("fa-"):
        fa_icon = "fa-" + fa_icon

    return fa_icon


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
            permissions = request.permissions or AgentPermissionConfig()  # type: ignore[call-arg]  # 所有參數都有默認值

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

            # 如果提供了 category_id，自動創建 AgentDisplayConfig（持久化到數據庫）
            if request.category_id:
                try:
                    display_store = AgentDisplayConfigStoreService()

                    # 檢查是否已存在（避免重複創建）
                    existing_config = display_store.get_agent_config(
                        agent_id=request.agent_id, tenant_id=None
                    )
                    if existing_config:
                        import logging

                        logging.warning(
                            f"Agent Display Config for agent '{request.agent_id}' already exists, skipping creation"
                        )
                    else:
                        # 獲取該分類下的現有 Agent 數量，用於計算 display_order
                        existing_agents = display_store.get_agents_by_category(
                            category_id=request.category_id, tenant_id=None, include_inactive=False
                        )
                        next_display_order = len(existing_agents)  # 新 Agent 放在最後

                        # 獲取 Agent 名稱和描述
                        agent_name = request.name
                        agent_description = (
                            request.metadata.description
                            if request.metadata and request.metadata.description
                            else agent_name
                        )

                        # 獲取圖標（轉換為 FontAwesome 格式）
                        icon_name = (
                            request.metadata.icon
                            if request.metadata and request.metadata.icon
                            else "FaRobot"
                        )
                        fa_icon = _react_icon_to_fa(icon_name)

                        # 創建 AgentConfig
                        agent_config = AgentConfig(
                            id=request.agent_id,
                            category_id=request.category_id,
                            display_order=next_display_order,
                            is_visible=True,
                            name=MultilingualText(
                                en=agent_name,
                                zh_CN=agent_name,
                                zh_TW=agent_name,
                            ),
                            description=MultilingualText(
                                en=agent_description,
                                zh_CN=agent_description,
                                zh_TW=agent_description,
                            ),
                            icon=fa_icon,
                            status="registering",  # 狀態為"審查中"
                            usage_count=0,
                            agent_id=request.agent_id,
                        )

                        # 創建 Display Config
                        display_store.create_agent(
                            agent_config=agent_config,
                            tenant_id=None,
                            created_by=user.user_id if user else None,
                        )
                        import logging

                        logging.info(
                            f"Agent Display Config created for agent '{request.agent_id}' in category '{request.category_id}'"
                        )
                except Exception as exc:
                    # 創建 Display Config 失敗不影響 Agent 註冊，只記錄警告
                    import logging

                    logging.warning(
                        f"Failed to create Agent Display Config for agent '{request.agent_id}': {exc}",
                        exc_info=True,
                    )

            return APIResponse.success(
                data={
                    "agent_id": request.agent_id,
                    "status": "registering",
                    "is_internal": request.endpoints.is_internal,
                    "protocol": (
                        request.endpoints.protocol.value if request.endpoints.protocol else None
                    ),
                    "secret_id": (request.permissions.secret_id if request.permissions else None),
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
                agent_info.endpoints.protocol.value if agent_info.endpoints.protocol else None
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


@router.get("/gateway/available-agents", status_code=http_status.HTTP_200_OK)
async def get_gateway_available_agents(
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    查詢 Cloudflare Gateway 上已配置但尚未在 AI-Box 註冊的 Agent

    從環境變數 MCP_GATEWAY_ROUTES 讀取 Gateway 路由配置，對比已註冊的 Agent，
    返回未註冊的 Agent 列表。

    Args:
        user: 當前認證用戶（可選）

    Returns:
        可用 Agent 列表，包含：
        - pattern: 工具名稱模式（如 warehouse_*）
        - target: 目標端點 URL
        - agent_name: 推斷的 Agent 名稱
        - is_registered: 是否已在 AI-Box 註冊
    """
    try:
        # 1. 從環境變數讀取 Gateway 路由配置
        mcp_routes_str = os.getenv("MCP_GATEWAY_ROUTES", "[]")

        try:
            mcp_routes = json.loads(mcp_routes_str)
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid MCP_GATEWAY_ROUTES format: {str(e)}",
            )

        if not isinstance(mcp_routes, list):
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="MCP_GATEWAY_ROUTES must be a JSON array",
            )

        # 2. 獲取已註冊的 Agent 列表
        registry = get_agent_registry()
        registered_agents = registry.get_all_agents()

        # 3. 構建已註冊 Agent 的工具前綴集合（用於比對）
        registered_patterns = set()
        for agent in registered_agents:
            # 檢查 Agent 是否使用 MCP 協議
            if (
                agent.endpoints
                and agent.endpoints.protocol
                and agent.endpoints.protocol.value == "mcp"
            ):
                # 從 capabilities 中提取工具前綴
                # 假設 capabilities 包含工具名稱，提取前綴（如 warehouse_execute_task -> warehouse_*）
                if agent.capabilities:
                    for capability in agent.capabilities:
                        # 提取前綴（去除 * 後的部分）
                        if "*" in capability:
                            prefix = capability.split("*")[0]
                            if prefix:
                                registered_patterns.add(prefix.rstrip("_") + "_*")
                        elif capability:
                            # 如果沒有 *，嘗試從工具名稱推斷前綴
                            parts = capability.split("_")
                            if len(parts) > 1:
                                prefix = parts[0] + "_*"
                                registered_patterns.add(prefix)

        # 4. 對比並構建可用 Agent 列表
        available_agents = []
        for route in mcp_routes:
            if not isinstance(route, dict):
                continue

            pattern = route.get("pattern", "")
            target = route.get("target", "")

            if not pattern or not target:
                continue

            # 推斷 Agent 名稱（從 pattern 中提取，如 warehouse_* -> Warehouse Agent）
            agent_name = pattern.replace("_*", "").replace("_", " ").title() + " Agent"
            if pattern.startswith("warehouse_"):
                agent_name = "庫管員 Agent"
            elif pattern.startswith("finance_"):
                agent_name = "財務 Agent"
            elif pattern.startswith("office_"):
                agent_name = "Office Agent"

            # 檢查是否已註冊（通過 pattern 比對）
            is_registered = pattern in registered_patterns

            # 如果未註冊，添加到可用列表
            if not is_registered:
                available_agents.append(
                    {
                        "pattern": pattern,
                        "target": target,
                        "agent_name": agent_name,
                        "is_registered": False,
                        "suggested_agent_id": pattern.replace("_*", "").replace("_", "-"),
                        "suggested_capabilities": [pattern.replace("*", "execute_task")],
                    }
                )

        return APIResponse.success(
            data={
                "available_agents": available_agents,
                "total": len(available_agents),
                "gateway_endpoint": os.getenv("MCP_GATEWAY_ENDPOINT", "https://mcp.k84.org"),
            },
            message=f"Found {len(available_agents)} available agents in Gateway",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query gateway available agents: {str(e)}",
        )


@router.get("/agents", status_code=http_status.HTTP_200_OK)
async def list_all_agents(
    status: Optional[AgentStatus] = Query(None, description="Agent 狀態過濾器"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取所有 Agent 列表（包括所有狀態）

    用於管理員查看和批准 Agent。可以通過 status 參數過濾特定狀態的 Agent。

    Args:
        status: Agent 狀態過濾器（可選，如不提供則返回所有狀態）
        user: 當前認證用戶（可選）

    Returns:
        Agent 列表
    """
    try:
        registry = get_agent_registry()
        all_agents = registry.get_all_agents()

        # 如果指定了狀態過濾器，進行過濾
        if status:
            filtered_agents = [agent for agent in all_agents if agent.status == status]
        else:
            filtered_agents = all_agents

        # 構建響應數據
        agents_data = []
        for agent in filtered_agents:
            agent_dict = agent.model_dump(mode="json")
            agent_dict["is_internal"] = agent.endpoints.is_internal
            agent_dict["protocol"] = (
                agent.endpoints.protocol.value if agent.endpoints.protocol else None
            )
            agents_data.append(agent_dict)

        return APIResponse.success(
            data={
                "agents": agents_data,
                "total": len(agents_data),
                "filtered_by_status": status.value if status else None,
            },
            message=f"Retrieved {len(agents_data)} agents",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}",
        )
