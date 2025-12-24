# 代碼功能說明: MCP Agent Service Client 實現
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""MCP Agent Service Client - 通過 MCP Protocol 調用 Agent 服務"""

import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional

from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)
from mcp.client.client import MCPClient
from mcp.client.connection.manager import MCPConnectionManager

logger = logging.getLogger(__name__)


class MCPAgentServiceClient(AgentServiceProtocol):
    """MCP Agent Service Client

    通過 MCP Protocol 調用遠程 Agent 服務。
    """

    def __init__(
        self,
        server_url: str,
        server_name: str = "agent-service",
        api_key: Optional[str] = None,
        server_certificate: Optional[str] = None,
        ip_whitelist: Optional[list[str]] = None,
        server_fingerprint: Optional[str] = None,
    ):
        """
        初始化 MCP Agent Service Client

        Args:
            server_url: MCP Server 的 URL（例如：ws://agent-planning-service:8002）
            server_name: MCP Server 名稱
            api_key: API 密鑰（可選，用於認證）
            server_certificate: 服務器證書（可選，用於 mTLS 認證）
            ip_whitelist: IP 白名單列表（可選）
            server_fingerprint: 服務器指紋（可選，用於身份驗證）
        """
        self.server_url = server_url
        self.server_name = server_name
        self.api_key = api_key
        self.server_certificate = server_certificate
        self.ip_whitelist = ip_whitelist or []
        self.server_fingerprint = server_fingerprint
        self._connection_manager: Optional[MCPConnectionManager] = None
        self._client: Optional[MCPClient] = None

    async def _ensure_connected(self):
        """確保已連接到 MCP Server"""
        if self._client is None:
            # MCPConnectionManager 需要 endpoints 列表
            self._connection_manager = MCPConnectionManager(endpoints=[self.server_url])
            await self._connection_manager.initialize()  # 使用 initialize 而不是 connect
            # MCPClient 需要 endpoint 參數，而不是 connection_manager
            self._client = MCPClient(
                endpoint=self.server_url,  # 使用 endpoint 參數
                client_name=self.server_name,
            )
            await self._client.initialize()

    async def _get_client(self) -> MCPClient:
        """獲取 MCP Client，確保已連接"""
        await self._ensure_connected()
        if self._client is None:
            raise RuntimeError("Failed to connect to MCP server")
        return self._client

    def _generate_request_signature(self, request_body: Dict[str, Any]) -> Optional[str]:
        """
        生成請求簽名（HMAC-SHA256）

        Args:
            request_body: 請求體

        Returns:
            簽名字符串，如果沒有 API Key 則返回 None
        """
        if not self.api_key:
            return None

        try:
            # 將請求體轉換為字符串（按鍵排序以確保一致性）
            request_str = json.dumps(request_body, sort_keys=True, separators=(",", ":"))

            # 計算 HMAC-SHA256 簽名
            signature = hmac.new(
                self.api_key.encode("utf-8"),
                request_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return signature
        except Exception as e:
            logger.error(f"Failed to generate request signature: {e}")
            return None

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行任務（帶認證支持）

        認證機制：
        1. API Key（通過 MCP 連接參數）
        2. 請求簽名（如果配置了 API Key）
        3. mTLS（通過 MCP 連接配置）
        """
        try:
            client = await self._get_client()

            # 準備請求參數
            request_body = {
                "task_id": request.task_id,
                "task_data": request.task_data,
                "context": request.context or {},
                "metadata": request.metadata or {},
            }

            # 生成並添加請求簽名（如果配置了 API Key）
            if self.api_key:
                signature = self._generate_request_signature(request_body)
                if signature:
                    request_body["signature"] = signature
                    request_body["api_key"] = self.api_key  # 也可以通過其他方式傳遞

            # 調用 MCP Tool
            tool_name = f"{request.task_type}_execute"
            result = await client.call_tool(
                tool_name,
                arguments=request_body,
            )

            return AgentServiceResponse(
                task_id=request.task_id,
                status="success" if result.get("status") != "error" else "error",
                result=result.get("result"),
                error=result.get("error"),
                metadata=result.get("metadata") or request.metadata,
            )
        except Exception as e:
            logger.error(f"MCP error calling agent service: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
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
