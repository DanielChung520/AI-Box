# 代碼功能說明: Agent Catalog API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Catalog API 路由 - 為前端 GenAI 提供 Agent 目錄查詢接口"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from services.api.core.response import APIResponse
from agents.services.registry.registry import get_agent_registry
from agents.services.registry.discovery import AgentDiscovery
from agents.services.registry.models import AgentStatus
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()

# 創建全局 Discovery 服務
_discovery_service: Optional[AgentDiscovery] = None


def get_discovery_service() -> AgentDiscovery:
    """獲取 Agent Discovery 服務實例"""
    global _discovery_service
    if _discovery_service is None:
        registry = get_agent_registry()
        _discovery_service = AgentDiscovery(registry)
    return _discovery_service


@router.get("/agents/catalog", status_code=http_status.HTTP_200_OK)
async def get_agent_catalog(
    category: Optional[str] = Query(None, description="Agent 分類"),
    capabilities: Optional[List[str]] = Query(None, description="需要的能力列表"),
    agent_type: Optional[str] = Query(None, description="Agent 類型"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取 Agent 目錄（供前端 GenAI 使用）

    返回所有可用的 Agent 信息，包含用途、權限、狀態等

    Args:
        category: Agent 分類過濾器
        capabilities: 需要的能力列表
        agent_type: Agent 類型過濾器
        user: 當前認證用戶（用於權限過濾）

    Returns:
        Agent 目錄數據
    """
    try:
        discovery = get_discovery_service()

        # 提取用戶信息
        user_id = user.user_id if user else None
        user_roles = user.roles if user and hasattr(user, "roles") else None

        # 發現 Agent
        agents = discovery.discover_agents(
            required_capabilities=capabilities,
            agent_type=agent_type,
            category=category,
            status=AgentStatus.ACTIVE,
            user_id=user_id,
            user_roles=user_roles,
        )

        # 構建目錄結構
        catalog = _build_catalog(agents)

        return APIResponse.success(
            data=catalog,
            message="Agent catalog retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent catalog: {str(e)}",
        )


@router.get("/agents/discover", status_code=http_status.HTTP_200_OK)
async def discover_agents(
    capabilities: Optional[List[str]] = Query(None, description="需要的能力列表"),
    agent_type: Optional[str] = Query(None, description="Agent 類型"),
    category: Optional[str] = Query(None, description="Agent 分類"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    發現可用的 Agent（增強版，支持權限過濾）

    Args:
        capabilities: 需要的能力列表
        agent_type: Agent 類型過濾器
        category: Agent 分類過濾器
        user: 當前認證用戶（用於權限過濾）

    Returns:
        匹配的 Agent 列表
    """
    try:
        discovery = get_discovery_service()

        # 提取用戶信息
        user_id = user.user_id if user else None
        user_roles = user.roles if user and hasattr(user, "roles") else None

        # 發現 Agent
        agents = discovery.discover_agents(
            required_capabilities=capabilities,
            agent_type=agent_type,
            category=category,
            status=AgentStatus.ACTIVE,
            user_id=user_id,
            user_roles=user_roles,
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


def _build_catalog(agents: List) -> Dict[str, Any]:
    """
    構建 Agent 目錄結構

    Args:
        agents: Agent 列表

    Returns:
        目錄結構字典
    """
    # 按分類組織 Agent
    categories: Dict[str, List[Dict[str, Any]]] = {}
    all_agents: List[Dict[str, Any]] = []

    for agent in agents:
        agent_dict = {
            "agent_id": agent.agent_id,
            "name": agent.metadata.name,
            "description": agent.metadata.description,
            "purpose": agent.metadata.purpose,
            "category": agent.metadata.category,
            "capabilities": agent.capabilities,
            "icon_url": agent.metadata.icon_url,
            "status": agent.status.value,
            "version": agent.metadata.version,
            "developer": agent.metadata.developer,
            "tags": agent.metadata.tags,
            "permission_type": agent.permissions.permission_type.value,
        }

        all_agents.append(agent_dict)

        # 按分類組織
        category = agent.metadata.category
        if category not in categories:
            categories[category] = []
        categories[category].append(agent_dict)

    # 構建目錄結構
    catalog_data = {
        "total_count": len(all_agents),
        "categories": [
            {
                "id": category_id,
                "name": category_id,  # 可以後續擴展為友好名稱
                "agents": agents_list,
                "count": len(agents_list),
            }
            for category_id, agents_list in categories.items()
        ],
        "agents": all_agents,
    }

    return catalog_data
