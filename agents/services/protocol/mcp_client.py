# 代碼功能說明: MCP Agent Service Client 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""MCP Agent Service Client - 通過 MCP Protocol 調用 Agent 服務"""

import logging
from typing import Any, Dict, Optional

from mcp.client.client import MCPClient
from mcp.client.connection.manager import MCPConnectionManager

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

logger = logging.getLogger(__name__)


class MCPAgentServiceClient(AgentServiceProtocol):
    """MCP Agent Service Client

    通過 MCP Protocol 調用遠程 Agent 服務。
    """

    def __init__(
        self,
        server_url: str,
        server_name: str = "agent-service",
    ):
        """
        初始化 MCP Agent Service Client

        Args:
            server_url: MCP Server 的 URL（例如：ws://agent-planning-service:8002）
            server_name: MCP Server 名稱
        """
        self.server_url = server_url
        self.server_name = server_name
        self._connection_manager: Optional[MCPConnectionManager] = None
        self._client: Optional[MCPClient] = None

    async def _ensure_connected(self):
        """確保已連接到 MCP Server"""
        if self._client is None:
            self._connection_manager = MCPConnectionManager()
            await self._connection_manager.connect(self.server_url)
            self._client = MCPClient(
                connection_manager=self._connection_manager,
                server_name=self.server_name,
            )
            await self._client.initialize()

    async def _get_client(self) -> MCPClient:
        """獲取 MCP Client，確保已連接"""
        await self._ensure_connected()
        if self._client is None:
            raise RuntimeError("Failed to connect to MCP server")
        return self._client

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """執行任務"""
        try:
            client = await self._get_client()
            # 調用 MCP Tool
            tool_name = f"{request.task_type}_execute"
            result = await client.call_tool(
                tool_name,
                arguments={
                    "task_id": request.task_id,
                    "task_data": request.task_data,
                    "context": request.context or {},
                    "metadata": request.metadata or {},
                },
            )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="success",
                result=result.get("result"),
                metadata=result.get("metadata"),
            )
        except Exception as e:
            logger.error(f"MCP error calling agent service: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                error=str(e),
            )

    async def health_check(self) -> AgentServiceStatus:
        """健康檢查"""
        try:
            client = await self._get_client()
            # 調用 health check tool
            result = await client.call_tool("health_check", arguments={})
            if result.get("status") == "healthy":
                return AgentServiceStatus.AVAILABLE
            return AgentServiceStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.UNAVAILABLE

    async def get_capabilities(self) -> Dict[str, Any]:
        """獲取服務能力"""
        try:
            client = await self._get_client()
            tools = await client.list_tools()
            return {
                "tools": [tool.name for tool in tools],
                "protocol": "mcp",
            }
        except Exception as e:
            logger.error(f"Failed to get capabilities: {e}")
            return {}

    async def close(self):
        """關閉客戶端連接"""
        if self._connection_manager:
            await self._connection_manager.close()
            self._connection_manager = None
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
