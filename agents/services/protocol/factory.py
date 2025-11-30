# 代碼功能說明: Agent Service Client Factory
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Service Client Factory - 創建不同類型的 Agent Service Client"""

from typing import Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceProtocolType,
)
from agents.services.protocol.http_client import HTTPAgentServiceClient
from agents.services.protocol.mcp_client import MCPAgentServiceClient


class AgentServiceClientFactory:
    """Agent Service Client Factory

    根據配置創建不同類型的 Agent Service Client。
    """

    @staticmethod
    def create(
        protocol: AgentServiceProtocolType,
        endpoint: str,
        **kwargs,
    ) -> AgentServiceProtocol:
        """
        創建 Agent Service Client

        Args:
            protocol: 協議類型（http 或 mcp）
            endpoint: 服務端點 URL
            **kwargs: 其他參數
                - timeout: HTTP 超時時間（僅 HTTP）
                - api_key: API 密鑰（僅 HTTP）
                - server_name: MCP Server 名稱（僅 MCP）

        Returns:
            Agent Service Client 實例

        Raises:
            ValueError: 如果協議類型不支持
        """
        if protocol == AgentServiceProtocolType.HTTP:
            return HTTPAgentServiceClient(
                base_url=endpoint,
                timeout=kwargs.get("timeout", 60.0),
                api_key=kwargs.get("api_key"),
            )
        elif protocol == AgentServiceProtocolType.MCP:
            return MCPAgentServiceClient(
                server_url=endpoint,
                server_name=kwargs.get("server_name", "agent-service"),
            )
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")
