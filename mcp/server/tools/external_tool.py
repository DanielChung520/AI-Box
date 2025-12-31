# 代碼功能說明: 外部 MCP 工具代理類
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-31

"""外部 MCP 工具代理類模組"""

import logging
import os
import time
from typing import Any, Dict, Optional

from mcp.client.client import MCPClient
from mcp.server.tools.base import BaseTool
from mcp.server.tools.metrics import get_tool_metrics
from mcp.server.tools.registry import get_registry

logger = logging.getLogger(__name__)


class ExternalMCPTool(BaseTool):
    """外部 MCP 工具代理類"""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        mcp_endpoint: str,
        tool_name_on_server: Optional[str] = None,
        mcp_client: Optional[MCPClient] = None,
        auth_config: Optional[Dict[str, Any]] = None,
        proxy_endpoint: Optional[str] = None,
        proxy_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化外部 MCP 工具

        Args:
            name: 工具名稱（本地別名）
            description: 工具描述
            input_schema: 輸入 Schema
            mcp_endpoint: 外部 MCP Server 端點（真實端點）
            tool_name_on_server: 外部服務器上的工具名稱（如果與本地名稱不同）
            mcp_client: MCP Client 實例（可選，自動創建）
            auth_config: 認證配置（API Key、OAuth 等）
            proxy_endpoint: 代理端點（如 Cloudflare Gateway，如果配置則使用此端點）
            proxy_config: 代理配置（審計、IP 隱藏等）
        """
        super().__init__(name, description, input_schema)
        self.mcp_endpoint = mcp_endpoint  # 真實端點（用於日誌和追蹤）
        self.proxy_endpoint = proxy_endpoint  # 代理端點（Gateway）
        self.proxy_config = proxy_config or {}
        # 如果配置了代理端點，使用代理端點；否則使用真實端點
        self.actual_endpoint = proxy_endpoint or mcp_endpoint
        self._tool_name_on_server = tool_name_on_server or name
        self._mcp_client = mcp_client
        self.auth_config = auth_config or {}
        self._initialized = False
        self._last_health_check: Optional[float] = None
        self._health_check_interval = 300  # 5 分鐘

    async def _get_client(self) -> MCPClient:
        """
        獲取或創建 MCP Client

        Returns:
            MCPClient: MCP Client 實例
        """
        if self._mcp_client is None or not self._initialized:
            # 創建新的 MCP Client（使用代理端點或真實端點）
            self._mcp_client = MCPClient(
                endpoint=self.actual_endpoint,
                timeout=30.0,
                max_retries=3,
                retry_delay=1.0,
            )

            # 如果使用代理，添加代理相關的請求頭
            if self.proxy_endpoint:
                proxy_headers = self._get_proxy_headers()
                if proxy_headers:
                    self._mcp_client.set_headers(proxy_headers)

            # 應用認證配置
            if self.auth_config:
                await self._apply_auth(self._mcp_client)

            # 初始化連接
            await self._mcp_client.initialize()
            self._initialized = True
            logger.info(f"Initialized MCP client for external tool: {self.name}")

        return self._mcp_client

    async def _apply_auth(self, client: MCPClient) -> None:
        """
        應用認證配置到 MCP Client

        Args:
            client: MCP Client 實例
        """
        auth_type = self.auth_config.get("auth_type", "none")
        headers: Dict[str, str] = {}

        if auth_type == "api_key":
            api_key = self._resolve_env_var(self.auth_config.get("api_key", ""))
            header_name = self.auth_config.get("header_name", "Authorization")
            headers[header_name] = (
                f"Bearer {api_key}" if header_name == "Authorization" else api_key
            )
            logger.debug(f"API Key auth configured for {self.name}")

        elif auth_type == "bearer":
            token = self._resolve_env_var(self.auth_config.get("token", ""))
            headers["Authorization"] = f"Bearer {token}"
            logger.debug(f"Bearer token auth configured for {self.name}")

        elif auth_type == "oauth2":
            # OAuth 2.0 流程需要更複雜的實現
            # 這裡先使用 token（如果提供）
            token = self._resolve_env_var(self.auth_config.get("access_token", ""))
            if token:
                headers["Authorization"] = f"Bearer {token}"
            logger.debug(f"OAuth2 auth configured for {self.name}")

        # 應用請求頭
        if headers:
            client.set_headers(headers)

    def _resolve_env_var(self, value: str) -> str:
        """
        解析環境變數

        Args:
            value: 可能包含環境變數的值（如 "${API_KEY}"）

        Returns:
            str: 解析後的值
        """
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value

    def _get_proxy_headers(self) -> Dict[str, str]:
        """
        獲取代理相關的請求頭

        Returns:
            Dict[str, str]: 代理請求頭
        """
        headers: Dict[str, str] = {}

        # 如果啟用審計，添加審計標識
        if self.proxy_config.get("audit_enabled", False):
            headers["X-Audit-Enabled"] = "true"
            headers["X-Tool-Name"] = self.name
            headers["X-Real-Endpoint"] = self.mcp_endpoint  # 真實端點（用於 Gateway 路由）

        # 如果啟用 IP 隱藏，添加標識
        if self.proxy_config.get("hide_ip", False):
            headers["X-Hide-IP"] = "true"

        return headers

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行外部工具（通過 MCP Protocol）

        Args:
            arguments: 工具參數

        Returns:
            Dict[str, Any]: 執行結果
        """
        # 驗證輸入
        if not self.validate_input(arguments):
            raise ValueError("Invalid input arguments")

        # 獲取 MCP Client
        client = await self._get_client()

        # 調用外部工具
        start_time = time.time()
        try:
            result = await client.call_tool(name=self._tool_name_on_server, arguments=arguments)
            latency_ms = (time.time() - start_time) * 1000

            # 記錄成功調用
            metrics = get_tool_metrics()
            metrics.record_call(self.name, success=True, latency_ms=latency_ms)

            # 更新註冊表統計
            registry = get_registry()
            registry.record_tool_call(self.name, success=True)

            logger.info(
                f"External tool '{self.name}' executed successfully "
                f"(latency: {latency_ms:.2f}ms)"
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__

            # 記錄失敗調用
            metrics = get_tool_metrics()
            metrics.record_call(
                self.name, success=False, latency_ms=latency_ms, error_type=error_type
            )

            # 更新註冊表統計
            registry = get_registry()
            registry.record_tool_call(self.name, success=False)

            logger.error(f"Failed to execute external tool '{self.name}': {e}")
            raise

    async def verify_connection(self) -> bool:
        """
        驗證外部 MCP Server 連接

        Returns:
            bool: 連接是否可用
        """
        try:
            client = await self._get_client()
            tools = await client.list_tools()

            # 檢查工具是否存在於外部服務器
            tool_names = [tool.name for tool in tools]
            if self._tool_name_on_server not in tool_names:
                logger.warning(
                    f"Tool '{self._tool_name_on_server}' not found on "
                    f"external MCP Server {self.mcp_endpoint}"
                )
                return False

            self._last_health_check = time.time()
            return True

        except Exception as e:
            logger.error(f"Failed to verify connection for external tool '{self.name}': {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        執行健康檢查

        Returns:
            Dict[str, Any]: 健康狀態信息
        """
        # 如果最近檢查過，直接返回緩存結果
        if (
            self._last_health_check
            and time.time() - self._last_health_check < self._health_check_interval
        ):
            return {"status": "healthy", "cached": True}

        try:
            start_time = time.time()
            is_healthy = await self.verify_connection()
            latency_ms = (time.time() - start_time) * 1000

            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "type": "external",
                "latency_ms": latency_ms,
                "endpoint": self.mcp_endpoint,  # 真實端點
                "proxy_endpoint": self.proxy_endpoint,  # 代理端點
                "actual_endpoint": self.actual_endpoint,  # 實際使用的端點
                "cached": False,
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "type": "external",
                "error": str(e),
                "endpoint": self.mcp_endpoint,  # 真實端點
                "proxy_endpoint": self.proxy_endpoint,  # 代理端點
                "actual_endpoint": self.actual_endpoint,  # 實際使用的端點
                "cached": False,
            }

    def get_info(self) -> Dict[str, Any]:
        """
        獲取工具信息（擴展版）

        Returns:
            Dict[str, Any]: 工具信息
        """
        info = super().get_info()
        info.update(
            {
                "type": "external",
                "mcp_endpoint": self.mcp_endpoint,  # 真實端點
                "proxy_endpoint": self.proxy_endpoint,  # 代理端點（如果配置）
                "actual_endpoint": self.actual_endpoint,  # 實際使用的端點
                "tool_name_on_server": self._tool_name_on_server,
                "auth_type": self.auth_config.get("auth_type", "none"),
                "proxy_enabled": self.proxy_endpoint is not None,
            }
        )
        return info

    async def close(self) -> None:
        """關閉 MCP Client 連接"""
        if self._mcp_client:
            await self._mcp_client.close()
            self._initialized = False
            logger.info(f"Closed MCP client for external tool: {self.name}")
