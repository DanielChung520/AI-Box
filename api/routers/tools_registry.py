# 代碼功能說明: 工具註冊清單 API 路由
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊清單 API 路由

提供工具註冊清單的查詢、註冊、更新、刪除等 API 接口。
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.tool_registry import (
    ToolRegistryCreate,
    ToolRegistryListResponse,
    ToolRegistryModel,
    ToolRegistryUpdate,
)
from services.api.services.tool_registry_store_service import get_tool_registry_store_service

router = APIRouter(prefix="/tools/registry", tags=["工具註冊清單"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ToolRegistryModel)
async def create_tool(tool: ToolRegistryCreate) -> JSONResponse:
    """
    註冊新工具

    Args:
        tool: 工具註冊數據

    Returns:
        創建的工具註冊記錄
    """
    try:
        service = get_tool_registry_store_service()
        created_tool = service.create_tool(tool)
        return APIResponse.success(
            data=created_tool.model_dump(mode="json"),
            message=f"Tool '{tool.name}' registered successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register tool: {str(e)}",
        )


@router.get("/{tool_name}", response_model=ToolRegistryModel)
async def get_tool(tool_name: str) -> JSONResponse:
    """
    獲取指定工具的註冊信息

    Args:
        tool_name: 工具名稱

    Returns:
        工具註冊記錄
    """
    try:
        service = get_tool_registry_store_service()
        tool = service.get_tool(tool_name)
        if tool is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool '{tool_name}' not found",
            )
        return APIResponse.success(
            data=tool.model_dump(mode="json"),
            message="Tool retrieved successfully",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool: {str(e)}",
        )


@router.put("/{tool_name}", response_model=ToolRegistryModel)
async def update_tool(tool_name: str, tool: ToolRegistryUpdate) -> JSONResponse:
    """
    更新工具註冊信息

    Args:
        tool_name: 工具名稱
        tool: 工具更新數據

    Returns:
        更新後的工具註冊記錄
    """
    try:
        service = get_tool_registry_store_service()
        updated_tool = service.update_tool(tool_name, tool)
        return APIResponse.success(
            data=updated_tool.model_dump(mode="json"),
            message=f"Tool '{tool_name}' updated successfully",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}",
        )


@router.delete("/{tool_name}", status_code=status.HTTP_200_OK)
async def delete_tool(tool_name: str) -> JSONResponse:
    """
    刪除工具註冊記錄（軟刪除）

    Args:
        tool_name: 工具名稱

    Returns:
        刪除結果
    """
    try:
        service = get_tool_registry_store_service()
        success = service.delete_tool(tool_name)
        if success:
            return APIResponse.success(
                data={"tool_name": tool_name},
                message=f"Tool '{tool_name}' deleted successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete tool '{tool_name}'",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}",
        )


@router.get("", response_model=ToolRegistryListResponse)
async def list_tools(
    category: Optional[str] = Query(None, description="工具類別（用於過濾）"),
    is_active: Optional[bool] = Query(True, description="是否只返回啟用的工具"),
    page: Optional[int] = Query(None, ge=1, description="頁碼（從 1 開始）"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每頁數量（最大 100）"),
) -> JSONResponse:
    """
    列出所有工具註冊記錄

    Args:
        category: 工具類別（可選，用於過濾）
        is_active: 是否只返回啟用的工具（默認 True）
        page: 頁碼（可選，用於分頁）
        page_size: 每頁數量（可選，用於分頁）

    Returns:
        工具註冊記錄列表
    """
    try:
        service = get_tool_registry_store_service()
        tools = service.list_tools(
            category=category,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        total = service.count_tools(category=category, is_active=is_active)

        response_data = {
            "tools": [tool.model_dump(mode="json") for tool in tools],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

        return APIResponse.success(
            data=response_data,
            message="Tools retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.get("/search", response_model=ToolRegistryListResponse)
async def search_tools(
    keyword: str = Query(..., description="搜索關鍵字"),
    is_active: Optional[bool] = Query(True, description="是否只返回啟用的工具"),
    page: Optional[int] = Query(None, ge=1, description="頁碼（從 1 開始）"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="每頁數量（最大 100）"),
) -> JSONResponse:
    """
    搜索工具（根據關鍵字搜索名稱、描述、用途、使用場景）

    Args:
        keyword: 搜索關鍵字
        is_active: 是否只返回啟用的工具（默認 True）
        page: 頁碼（可選，用於分頁）
        page_size: 每頁數量（可選，用於分頁）

    Returns:
        匹配的工具註冊記錄列表
    """
    try:
        service = get_tool_registry_store_service()
        tools = service.search_tools(
            keyword=keyword,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

        # 計算總數（用於分頁）
        total = len(tools) if page is None else service.count_tools(is_active=is_active)

        response_data = {
            "tools": [tool.model_dump(mode="json") for tool in tools],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

        return APIResponse.success(
            data=response_data,
            message=f"Found {len(tools)} tools matching '{keyword}'",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search tools: {str(e)}",
        )


@router.get("/categories/list", response_model=List[str])
async def list_categories() -> JSONResponse:
    """
    列出所有工具類別

    Returns:
        工具類別列表
    """
    try:
        service = get_tool_registry_store_service()
        tools = service.list_tools(is_active=True)

        # 提取所有唯一的類別
        categories = sorted(set(tool.category for tool in tools))

        return APIResponse.success(
            data=categories,
            message="Categories retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list categories: {str(e)}",
        )
