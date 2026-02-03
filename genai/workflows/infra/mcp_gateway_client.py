# 代碼功能說明: MCP Gateway 客戶端
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""MCP Gateway 客戶端，用於安全調用外部 Agent。"""

import os
import logging
from typing import Any, Dict, List, Optional

from mcp.client.client import MCPClient

logger = logging.getLogger(__name__)


class MCPGatewayClient:
    """MCP Gateway 客戶端，實現安全認證和路由。"""

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        gateway_secret: Optional[str] = None,
    ):
        self.gateway_url = gateway_url or os.getenv(
            "MCP_GATEWAY_URL", "https://mcp-gateway.896445070.workers.dev"
        )
        self.gateway_secret = gateway_secret or os.getenv("MCP_GATEWAY_SECRET"),
        self._clients: Dict[str, MCPClient] = {}

    def _get_headers(
        self, user_id: str, tool_name: str, tenant_id: str = "default"
    ) -> Dict[str, str]:
        """構建 Gateway 認證 Headers。"""
        headers = {
            "Content-Type": "application/json",
            "X-User-ID": user_id,
            "X-Tenant-ID": tenant_id,
            "X-Tool-Name": tool_name,
        }
        if self.gateway_secret:
            headers["X-Gateway-Secret"] = self.gateway_secret
        return headers

    async def call_external_agent(
        self,
        agent_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: str,
        tenant_id: str = "default",
    ) -> Dict[str, Any]:
        """
        通過 Gateway 調用外部 Agent 工具。

        Args:
            agent_id: 外部 Agent ID
            tool_name: 工具名稱
            arguments: 工具參數
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            執行結果
        """
        headers = self._get_headers(user_id, tool_name, tenant_id)

        # 為了簡化，我們為每個請求創建或獲取一個客戶端
        # 實際項目中可以使用連接池
        if agent_id not in self._clients:
            client = MCPClient(endpoint=self.gateway_url, headers=headers)
            self._clients[agent_id] = client
        else:
            client = self._clients[agent_id]
            client.set_headers(headers)

        try:
            logger.info(f"Calling external agent {agent_id} via Gateway: tool={tool_name}")
            result = await client.call_tool(name=tool_name, arguments=arguments)
            return result
        except Exception as e:
            logger.error(f"Failed to call external agent {agent_id}: {e}", exc_info=True)
            return {"error": str(e), "status": "failed"}

    async def close_all(self):
        """關閉所有客戶端。"""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
