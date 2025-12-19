# 代碼功能說明: MCP 整合路由
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP 整合路由 - 展示如何在 FastAPI 中使用 MCP Client"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from services.api.core.response import APIResponse

logger = logging.getLogger(__name__)

# 嘗試導入 MCP Client（如果可用）
try:
    from mcp.client.connection.manager import MCPConnectionManager
    from mcp.client.connection.pool import LoadBalanceStrategy

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

router = APIRouter(prefix="/mcp", tags=["MCP"])

# 全局 MCP 連線管理器（單例模式）
_mcp_manager: Optional[MCPConnectionManager] = None


def get_mcp_manager() -> Optional[MCPConnectionManager]:
    """
    獲取 MCP 連線管理器實例

    Returns:
        MCPConnectionManager: 連線管理器實例，如果 MCP 不可用則返回 None
    """
    global _mcp_manager

    if not MCP_AVAILABLE:
        return None

    if _mcp_manager is None:
        # 從環境變數獲取 MCP Server 端點
        mcp_endpoints = os.getenv("MCP_SERVER_ENDPOINTS", "http://mcp-server:8002/mcp").split(",")

        _mcp_manager = MCPConnectionManager(
            endpoints=mcp_endpoints,
            load_balance_strategy=LoadBalanceStrategy.ROUND_ROBIN,
            health_check_interval=30,
            max_retries=3,
            retry_delay=1.0,
        )

    return _mcp_manager


class MCPToolCallRequest(BaseModel):
    """MCP 工具調用請求"""

    tool_name: str
    arguments: Dict[str, Any]


class MCPListToolsResponse(BaseModel):
    """MCP 工具列表響應"""

    tools: List[Dict[str, Any]]


@router.get("/status", status_code=status.HTTP_200_OK)
async def mcp_status():
    """
    獲取 MCP 連線狀態

    Returns:
        MCP 連線狀態信息
    """
    if not MCP_AVAILABLE:
        return APIResponse.success(
            data={"available": False, "message": "MCP Client not available"},
            message="MCP status retrieved",
        )

    manager = get_mcp_manager()
    if manager is None:
        return APIResponse.success(
            data={"available": False, "message": "MCP Manager not initialized"},
            message="MCP status retrieved",
        )

    try:
        stats = manager.get_stats()
        return APIResponse.success(
            data={
                "available": True,
                "stats": stats,
            },
            message="MCP status retrieved",
        )
    except Exception as e:
        return APIResponse.success(
            data={
                "available": False,
                "error": str(e),
            },
            message="MCP status retrieved",
        )


@router.get("/tools", status_code=status.HTTP_200_OK)
async def list_mcp_tools():
    """
    列出 MCP Server 可用工具

    Returns:
        工具列表
    """
    if not MCP_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP Client not available",
        )

    manager = get_mcp_manager()
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP Manager not initialized",
        )

    try:
        # 初始化連線（如果尚未初始化）
        if not manager.pool._initialized:
            await manager.initialize()

        tools = await manager.list_tools()
        tools_data = [tool.model_dump() if hasattr(tool, "model_dump") else tool for tool in tools]

        return APIResponse.success(
            data={"tools": tools_data},
            message="Tools retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.post("/tools/call", status_code=status.HTTP_200_OK)
async def call_mcp_tool(request: MCPToolCallRequest):
    """
    調用 MCP 工具

    Args:
        request: 工具調用請求

    Returns:
        工具執行結果
    """
    if not MCP_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP Client not available",
        )

    manager = get_mcp_manager()
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MCP Manager not initialized",
        )

    try:
        # 初始化連線（如果尚未初始化）
        if not manager.pool._initialized:
            await manager.initialize()

        result = await manager.call_tool(
            name=request.tool_name,
            arguments=request.arguments,
        )

        return APIResponse.success(
            data={"result": result},
            message=f"Tool '{request.tool_name}' executed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to call tool: {str(e)}",
        )


@router.on_event("startup")
async def startup_mcp():
    """啟動時初始化 MCP 連線（非阻塞）"""
    if MCP_AVAILABLE:
        manager = get_mcp_manager()
        if manager:
            try:
                # 使用 asyncio.create_task 在后台初始化，不阻塞应用启动
                import asyncio

                asyncio.create_task(_initialize_mcp_background(manager))
            except Exception as e:
                logger.warning(f"Failed to start MCP initialization: {e}")


async def _initialize_mcp_background(manager):
    """在后台初始化 MCP 连接"""
    try:
        await manager.initialize()
        logger.info("MCP connection initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize MCP connection (will retry later): {e}")


@router.on_event("shutdown")
async def shutdown_mcp():
    """關閉時清理 MCP 連線"""
    global _mcp_manager
    if _mcp_manager:
        try:
            await _mcp_manager.close()
        except Exception as e:
            print(f"Failed to close MCP connection: {e}")
        finally:
            _mcp_manager = None
