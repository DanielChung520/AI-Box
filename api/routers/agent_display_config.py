# 代碼功能說明: Agent Display Config API 路由
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Agent Display Config API 路由 - 為前端提供代理展示配置管理接口"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.agent_display_config import AgentConfig, CategoryConfig
from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()

# 創建全局 Store Service
_store_service: Optional[AgentDisplayConfigStoreService] = None


def get_store_service() -> AgentDisplayConfigStoreService:
    """獲取 Agent Display Config Store Service 實例"""
    global _store_service
    if _store_service is None:
        _store_service = AgentDisplayConfigStoreService()
    return _store_service


@router.get("/agent-display-configs", status_code=http_status.HTTP_200_OK)
async def get_agent_display_configs(
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    include_inactive: bool = Query(False, description="是否包含未啟用的配置"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取完整的代理展示配置

    返回所有分類和代理的展示配置，用於前端渲染代理展示區。

    Args:
        tenant_id: 租戶 ID（可選，None 表示系統級）
        include_inactive: 是否包含未啟用的配置
        user: 當前認證用戶

    Returns:
        完整的展示配置（分類 + 代理）
    """
    try:
        store = get_store_service()
        config = store.get_all_display_config(
            tenant_id=tenant_id, include_inactive=include_inactive
        )

        return APIResponse.success(
            data=config,
            message="Agent display config retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent display config: {str(e)}",
        )


@router.get("/agent-display-configs/categories", status_code=http_status.HTTP_200_OK)
async def get_categories(
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    include_inactive: bool = Query(False, description="是否包含未啟用的配置"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取分類列表

    Args:
        tenant_id: 租戶 ID（可選，None 表示系統級）
        include_inactive: 是否包含未啟用的配置
        user: 當前認證用戶

    Returns:
        分類列表
    """
    try:
        store = get_store_service()
        categories = store.get_categories(tenant_id=tenant_id, include_inactive=include_inactive)

        return APIResponse.success(
            data={"categories": [cat.model_dump() for cat in categories]},
            message="Categories retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {str(e)}",
        )


@router.get(
    "/agent-display-configs/categories/{category_id}/agents",
    status_code=http_status.HTTP_200_OK,
)
async def get_agents_by_category(
    category_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    include_inactive: bool = Query(False, description="是否包含未啟用的配置"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取指定分類下的代理列表

    Args:
        category_id: 分類 ID
        tenant_id: 租戶 ID（可選，None 表示系統級）
        include_inactive: 是否包含未啟用的配置
        user: 當前認證用戶

    Returns:
        代理列表
    """
    try:
        store = get_store_service()
        agents = store.get_agents_by_category(
            category_id=category_id, tenant_id=tenant_id, include_inactive=include_inactive
        )

        return APIResponse.success(
            data={"agents": [agent.model_dump() for agent in agents]},
            message="Agents retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agents: {str(e)}",
        )


@router.post("/agent-display-configs/categories", status_code=http_status.HTTP_201_CREATED)
async def create_category(
    category_config: CategoryConfig,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    創建分類配置

    需要管理員權限。

    Args:
        category_config: 分類配置
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        創建結果
    """
    try:
        # TODO: 檢查管理員權限
        # if not user or not user.has_permission("agent:display_config:create"):
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        config_key = store.create_category(
            category_config=category_config,
            tenant_id=tenant_id,
            created_by=user.user_id if user else None,
        )

        return APIResponse.success(
            data={"config_key": config_key},
            message="Category created successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create category: {str(e)}",
        )


@router.put(
    "/agent-display-configs/categories/{category_id}",
    status_code=http_status.HTTP_200_OK,
)
async def update_category(
    category_id: str,
    category_config: CategoryConfig,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    更新分類配置

    需要管理員權限。

    Args:
        category_id: 分類 ID
        category_config: 分類配置
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        更新結果
    """
    try:
        # TODO: 檢查管理員權限
        # if not user or not user.has_permission("agent:display_config:update"):
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        success = store.update_category(
            category_id=category_id,
            category_config=category_config,
            tenant_id=tenant_id,
            updated_by=user.user_id if user else None,
        )

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} not found",
            )

        return APIResponse.success(
            data={"category_id": category_id},
            message="Category updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update category: {str(e)}",
        )


@router.delete(
    "/agent-display-configs/categories/{category_id}",
    status_code=http_status.HTTP_200_OK,
)
async def delete_category(
    category_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    刪除分類配置（軟刪除）

    需要管理員權限。

    Args:
        category_id: 分類 ID
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        # TODO: 檢查管理員權限
        # if not user or not user.has_permission("agent:display_config:delete"):
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        success = store.delete_category(category_id=category_id, tenant_id=tenant_id)

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} not found",
            )

        return APIResponse.success(
            data={"category_id": category_id},
            message="Category deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete category: {str(e)}",
        )


@router.post("/agent-display-configs/agents", status_code=http_status.HTTP_201_CREATED)
async def create_agent(
    agent_config: AgentConfig,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    創建代理配置

    需要管理員權限。

    Args:
        agent_config: 代理配置
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        創建結果
    """
    try:
        # TODO: 檢查管理員權限
        # if not user or not user.has_permission("agent:display_config:create"):
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        config_key = store.create_agent(
            agent_config=agent_config,
            tenant_id=tenant_id,
            created_by=user.user_id if user else None,
        )

        return APIResponse.success(
            data={"config_key": config_key},
            message="Agent config created successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent config: {str(e)}",
        )


@router.put(
    "/agent-display-configs/agents/{agent_id}",
    status_code=http_status.HTTP_200_OK,
)
async def update_agent(
    agent_id: str,
    agent_config: AgentConfig,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    更新代理配置

    需要管理員權限。

    Args:
        agent_id: 代理 ID
        agent_config: 代理配置
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        更新結果
    """
    try:
        # TODO: 檢查管理員權限
        # if not user or not user.has_permission("agent:display_config:update"):
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        success = store.update_agent(
            agent_id=agent_id,
            agent_config=agent_config,
            tenant_id=tenant_id,
            updated_by=user.user_id if user else None,
        )

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent config {agent_id} not found",
            )

        return APIResponse.success(
            data={"agent_id": agent_id},
            message="Agent config updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent config: {str(e)}",
        )


@router.delete(
    "/agent-display-configs/agents/{agent_id}",
    status_code=http_status.HTTP_200_OK,
)
async def delete_agent(
    agent_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    刪除代理配置（軟刪除）

    需要管理員權限。

    Args:
        agent_id: 代理 ID
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        # TODO: 檢查管理員權限
        # if not user or not user.has_permission("agent:display_config:delete"):
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        success = store.delete_agent(agent_id=agent_id, tenant_id=tenant_id)

        if not success:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent config {agent_id} not found",
            )

        return APIResponse.success(
            data={"agent_id": agent_id},
            message="Agent config deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent config: {str(e)}",
        )


@router.get(
    "/agent-display-configs/agents/{agent_id}",
    status_code=http_status.HTTP_200_OK,
)
async def get_agent_config(
    agent_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取單個代理配置

    Args:
        agent_id: 代理 ID
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        代理配置
    """
    try:
        store = get_store_service()
        agent_config = store.get_agent_config(agent_id=agent_id, tenant_id=tenant_id)

        if agent_config is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent config {agent_id} not found",
            )

        return APIResponse.success(
            data=agent_config.model_dump(),
            message="Agent config retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent config: {str(e)}",
        )
