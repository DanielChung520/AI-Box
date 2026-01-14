# 代碼功能說明: Agent Category API 路由
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Agent Category API 路由 - 為前端提供代理分類管理接口

分類由系統管理員管理，包括：人力資源、物流、財務、生產管理、經寶PoC等。
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.agent_category import AgentCategory
from services.api.services.agent_category_store_service import AgentCategoryStoreService
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()

# 創建全局 Store Service
_store_service: Optional[AgentCategoryStoreService] = None


def get_store_service() -> AgentCategoryStoreService:
    """獲取 Agent Category Store Service 實例"""
    global _store_service
    if _store_service is None:
        _store_service = AgentCategoryStoreService()
    return _store_service


@router.get("/agent-categories", status_code=http_status.HTTP_200_OK)
async def get_categories(
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    include_inactive: bool = Query(False, description="是否包含未啟用的分類"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取分類列表

    Args:
        tenant_id: 租戶 ID（可選，None 表示系統級）
        include_inactive: 是否包含未啟用的分類
        user: 當前認證用戶

    Returns:
        分類列表
    """
    try:
        store = get_store_service()
        categories = store.get_categories(tenant_id=tenant_id, include_inactive=include_inactive)

        return APIResponse.success(
            data={"categories": [cat.model_dump() for cat in categories]},
            message="Agent categories retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent categories: {str(e)}",
        )


@router.get("/agent-categories/{category_id}", status_code=http_status.HTTP_200_OK)
async def get_category(
    category_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取單個分類

    Args:
        category_id: 分類 ID
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶

    Returns:
        分類配置
    """
    try:
        store = get_store_service()
        category = store.get_category(category_id=category_id, tenant_id=tenant_id)

        if category is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Category {category_id} not found",
            )

        return APIResponse.success(
            data=category.model_dump(),
            message="Agent category retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent category: {str(e)}",
        )


@router.post("/agent-categories", status_code=http_status.HTTP_201_CREATED)
async def create_category(
    category: AgentCategory,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    創建分類

    需要系統管理員權限。

    Args:
        category: 分類配置
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶（系統管理員）

    Returns:
        創建結果
    """
    try:
        # TODO: 檢查系統管理員權限
        # if not user or not user.is_admin:
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        config_key = store.create_category(
            category=category,
            tenant_id=tenant_id,
            created_by=user.user_id if user else None,
        )

        return APIResponse.success(
            data={"config_key": config_key},
            message="Agent category created successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent category: {str(e)}",
        )


@router.put(
    "/agent-categories/{category_id}",
    status_code=http_status.HTTP_200_OK,
)
async def update_category(
    category_id: str,
    category: AgentCategory,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    更新分類

    需要系統管理員權限。

    Args:
        category_id: 分類 ID
        category: 分類配置
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶（系統管理員）

    Returns:
        更新結果
    """
    try:
        # TODO: 檢查系統管理員權限
        # if not user or not user.is_admin:
        #     raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="Permission denied")

        store = get_store_service()
        success = store.update_category(
            category_id=category_id,
            category=category,
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
            message="Agent category updated successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent category: {str(e)}",
        )


@router.delete(
    "/agent-categories/{category_id}",
    status_code=http_status.HTTP_200_OK,
)
async def delete_category(
    category_id: str,
    tenant_id: Optional[str] = Query(None, description="租戶 ID"),
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    刪除分類（軟刪除）

    需要系統管理員權限。

    Args:
        category_id: 分類 ID
        tenant_id: 租戶 ID（可選，None 表示系統級）
        user: 當前認證用戶（系統管理員）

    Returns:
        刪除結果
    """
    try:
        # TODO: 檢查系統管理員權限
        # if not user or not user.is_admin:
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
            message="Agent category deleted successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent category: {str(e)}",
        )
