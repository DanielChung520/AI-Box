# 代碼功能說明: MCP Client 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Client 核心實現"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from mcp.server.protocol.models import (
    MCPInitializeRequest,
    MCPListToolsRequest,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPToolCallRequest,
)

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP Client 實現類"""

    def __init__(
        self,
        endpoint: str,
        client_name: str = "ai-box-client",
        client_version: str = "1.0.0",
        timeout: float = 30.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        auto_reconnect: bool = True,
    ):
        """
        初始化 MCP Client

        Args:
            endpoint: MCP Server 端點 URL
            client_name: 客戶端名稱
            client_version: 客戶端版本
            timeout: 請求超時時間（秒）
            max_retries: 最大重試次數
            retry_delay: 重試延遲（秒）
            auto_reconnect: 是否自動重連
        """
        self.endpoint = endpoint
        self.client_name = client_name
        self.client_version = client_version
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.auto_reconnect = auto_reconnect
        self.client = httpx.AsyncClient(timeout=timeout)
        self.initialized = False
        self.protocol_version: Optional[str] = None
        self.server_info: Optional[Dict[str, Any]] = None
        self.tools: List[MCPTool] = []
        self.request_id_counter = 0

    async def initialize(self) -> Dict[str, Any]:
        """
        初始化與 MCP Server 的連接

        Returns:
            初始化結果
        """
        if self.initialized:
            logger.warning("Client already initialized")
            return {
                "protocolVersion": self.protocol_version,
                "serverInfo": self.server_info,
            }

        request = MCPInitializeRequest(
            id=1,
            params={
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
            },
        )

        response = await self._send_request(request)
        if response.result:
            self.protocol_version = response.result.get("protocolVersion")
            self.server_info = response.result.get("serverInfo")
        self.initialized = True

        # 獲取工具列表
        await self.refresh_tools()

        logger.info(f"Initialized MCP client, connected to {self.endpoint}")
        return response.result or {}

    def _generate_request_id(self) -> int:
        """
        生成請求 ID

        Returns:
            int: 請求 ID
        """
        self.request_id_counter += 1
        return self.request_id_counter

    async def _send_request(self, request: MCPRequest, retry_count: int = 0) -> MCPResponse:
        """
        發送 MCP 請求（帶重試機制）

        Args:
            request: MCP 請求對象
            retry_count: 當前重試次數

        Returns:
            MCP 響應對象
        """
        try:
            # 確保請求有 ID
            if request.id is None:
                request.id = self._generate_request_id()

            response = await self.client.post(
                self.endpoint, json=request.model_dump(exclude_none=True)
            )
            response.raise_for_status()
            response_data = response.json()
            return MCPResponse(**response_data)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            # 網絡錯誤，嘗試重連
            if self.auto_reconnect and retry_count < self.max_retries:
                logger.warning(
                    f"Connection error, retrying ({retry_count + 1}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                # 重新初始化連接
                if not self.initialized:
                    await self.initialize()
                return await self._send_request(request, retry_count + 1)
            logger.error(f"Failed to send MCP request after {retry_count + 1} retries: {e}")
            raise
        except httpx.HTTPStatusError as e:
            # HTTP 錯誤，不重試
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Failed to send MCP request: {e}")
            raise

    async def refresh_tools(self) -> List[MCPTool]:
        """
        刷新工具列表

        Returns:
            工具列表
        """
        request = MCPListToolsRequest(id=2)
        response = await self._send_request(request)
        if response.result:
            tools_data = response.result.get("tools", [])
            self.tools = [MCPTool(**tool) for tool in tools_data]
        else:
            self.tools = []
        logger.info(f"Refreshed tools list, found {len(self.tools)} tools")
        return self.tools

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        調用工具

        Args:
            name: 工具名稱
            arguments: 工具參數

        Returns:
            工具執行結果
        """
        if not self.initialized:
            await self.initialize()

        request = MCPToolCallRequest(id=3, params={"name": name, "arguments": arguments})

        response = await self._send_request(request)
        if not response.result:
            return {}
        result = response.result.get("content", [])

        # 解析結果
        if result and len(result) > 0:
            content = result[0]
            if content.get("type") == "text":
                try:
                    return json.loads(content.get("text", "{}"))
                except Exception:
                    return {"text": content.get("text", "")}

        return response.result

    async def list_tools(self) -> List[MCPTool]:
        """
        列出可用工具

        Returns:
            工具列表
        """
        if not self.initialized:
            await self.initialize()
        return self.tools

    async def close(self) -> None:
        """關閉客戶端連接"""
        await self.client.aclose()
        self.initialized = False
        logger.info("MCP client closed")
