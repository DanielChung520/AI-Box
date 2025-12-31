# 代碼功能說明: MCP Server 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Server 核心實現"""

import json
import logging
import time
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .protocol.models import (
    MCPError,
    MCPErrorResponse,
    MCPInitializeResponse,
    MCPListToolsResponse,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPToolCallResponse,
)

logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server 實現類"""

    def __init__(
        self,
        name: str = "ai-box-server",
        version: str = "1.0.0",
        protocol_version: str = "2024-11-05",
        enable_monitoring: bool = True,
        metrics_callback: Optional[Callable] = None,
    ):
        """
        初始化 MCP Server

        Args:
            name: 服務器名稱
            version: 服務器版本
            protocol_version: MCP Protocol 版本
            enable_monitoring: 是否啟用監控
            metrics_callback: 指標回調函數
        """
        self.name = name
        self.version = version
        self.protocol_version = protocol_version
        self.tools: Dict[str, MCPTool] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.enable_monitoring = enable_monitoring
        self.metrics_callback = metrics_callback
        self.app = FastAPI(title=f"{name} MCP Server")
        self._setup_routes()
        self._setup_health_routes()

    def _setup_routes(self):
        """設置路由"""

        @self.app.post("/mcp")
        async def handle_mcp_request(request: Request):
            """處理 MCP 請求"""
            start_time = time.time()
            body = None
            is_error = False

            try:
                body = await request.json()
                mcp_request = MCPRequest(**body)
                response = await self._handle_request(mcp_request)

                # 記錄指標
                if self.enable_monitoring and self.metrics_callback:
                    latency = time.time() - start_time
                    method = mcp_request.method
                    self.metrics_callback(method, latency, is_error)

                return JSONResponse(content=response.model_dump(exclude_none=True))
            except Exception as e:
                is_error = True
                logger.error(f"Error handling MCP request: {e}")

                # 記錄錯誤指標
                if self.enable_monitoring and self.metrics_callback:
                    latency = time.time() - start_time
                    method = body.get("method", "unknown") if body else "unknown"
                    self.metrics_callback(method, latency, is_error)

                error_response = MCPErrorResponse(
                    id=body.get("id") if body else None,
                    error=MCPError(
                        code=-32603,
                        message="Internal error",
                        data={"error": str(e)},
                    ),
                )
                return JSONResponse(
                    content=error_response.model_dump(exclude_none=True),
                    status_code=500,
                )

    def _setup_health_routes(self):
        """設置健康檢查路由"""

        @self.app.get("/health")
        async def health_check():
            """健康檢查端點"""
            return {
                "status": "healthy",
                "server": self.name,
                "version": self.version,
                "protocol_version": self.protocol_version,
                "tools_count": len(self.tools),
            }

        @self.app.get("/ready")
        async def readiness_check():
            """就緒檢查端點"""
            return {
                "status": "ready",
                "server": self.name,
            }

        @self.app.get("/metrics/tools")
        async def tools_metrics():
            """工具調用統計端點"""
            from mcp.server.tools.metrics import get_tool_metrics

            metrics = get_tool_metrics()
            return {
                "summary": metrics.get_summary(),
                "tools": metrics.get_stats(),
            }

        @self.app.get("/metrics/tools/{tool_name}")
        async def tool_metrics(tool_name: str):
            """單個工具調用統計端點"""
            from fastapi import HTTPException, status

            from mcp.server.tools.metrics import get_tool_metrics

            metrics = get_tool_metrics()
            stats = metrics.get_stats(tool_name)
            if not stats:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Tool '{tool_name}' not found or has no statistics",
                )
            return stats

    async def _handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        處理 MCP 請求

        Args:
            request: MCP 請求對象

        Returns:
            MCP 響應對象
        """
        method = request.method

        if method == "initialize":
            return await self._handle_initialize(request)
        elif method == "tools/list":
            return await self._handle_list_tools(request)
        elif method == "tools/call":
            return await self._handle_tool_call(request)
        else:
            raise ValueError(f"Unknown method: {method}")

    async def _handle_initialize(self, request: MCPRequest) -> MCPInitializeResponse:
        """處理初始化請求"""
        return MCPInitializeResponse(
            id=request.id,
            result={
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "serverInfo": {"name": self.name, "version": self.version},
            },
        )

    async def _handle_list_tools(self, request: MCPRequest) -> MCPListToolsResponse:
        """處理列出工具請求"""
        tools_list = [tool.model_dump() for tool in self.tools.values()]
        return MCPListToolsResponse(id=request.id, result={"tools": tools_list})

    async def _handle_tool_call(self, request: MCPRequest) -> MCPToolCallResponse:
        """處理工具調用請求"""
        import time

        from mcp.server.tools.metrics import get_tool_metrics
        from mcp.server.tools.registry import get_registry

        params = request.params or {}
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name not in self.tool_handlers:
            raise ValueError(f"Tool '{tool_name}' not found")

        handler = self.tool_handlers[tool_name]

        # 記錄調用開始時間
        start_time = time.time()
        metrics = get_tool_metrics()
        registry = get_registry()

        try:
            result = await handler(arguments)
            latency_ms = (time.time() - start_time) * 1000

            # 記錄成功調用
            metrics.record_call(tool_name, success=True, latency_ms=latency_ms)
            registry.record_tool_call(tool_name, success=True)

            return MCPToolCallResponse(
                id=request.id,
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                json.dumps(result) if isinstance(result, dict) else str(result)
                            ),
                        }
                    ]
                },
            )
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_type = type(e).__name__

            # 記錄失敗調用
            metrics.record_call(
                tool_name, success=False, latency_ms=latency_ms, error_type=error_type
            )
            registry.record_tool_call(tool_name, success=False)

            # 重新拋出異常
            raise

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        handler: Callable,
    ) -> None:
        """
        註冊工具

        Args:
            name: 工具名稱
            description: 工具描述
            input_schema: 輸入 Schema
            handler: 工具處理函數
        """
        tool = MCPTool(name=name, description=description, inputSchema=input_schema)
        self.tools[name] = tool
        self.tool_handlers[name] = handler
        logger.info(f"Registered tool: {name}")

    def get_fastapi_app(self) -> FastAPI:
        """
        獲取 FastAPI 應用實例

        Returns:
            FastAPI 應用
        """
        return self.app
