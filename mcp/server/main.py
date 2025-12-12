# 代碼功能說明: MCP Server 啟動入口
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Server 啟動入口文件"""

import logging
import argparse
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional

from .server import MCPServer
from .config import get_config
from .monitoring import get_metrics
from .tools.registry import get_registry
from .tools.task_analyzer import TaskAnalyzerTool
from .tools.file_tool import FileTool

# 修改時間：2025-12-08 12:30:00 UTC+8 - 使用統一的日誌配置模組
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from system.logging_config import setup_mcp_server_logging

# 配置 MCP Server 日誌（使用 RotatingFileHandler，最大 500KB，保留 4 個備份）
setup_mcp_server_logging()
logger = logging.getLogger(__name__)

# 全局應用實例
_app_instance: Optional[MCPServer] = None


@asynccontextmanager
async def lifespan(app):
    """應用生命週期管理"""
    # 啟動時
    logger.info("Starting MCP Server...")
    yield
    # 關閉時
    logger.info("Shutting down MCP Server...")


def create_app(config=None) -> MCPServer:
    """
    創建 MCP Server 應用實例

    Args:
        config: 配置實例，如果為 None 則從環境變數讀取

    Returns:
        MCPServer: MCP Server 實例
    """
    global _app_instance

    if config is None:
        config = get_config()

    # 獲取指標實例
    metrics = get_metrics()

    # 創建 MCP Server 實例
    server = MCPServer(
        name=config.server_name,
        version=config.server_version,
        protocol_version=config.protocol_version,
        enable_monitoring=config.enable_monitoring,
        metrics_callback=metrics.record_request if config.enable_monitoring else None,
    )

    # 添加指標端點
    if config.enable_monitoring:

        @server.app.get(config.metrics_endpoint)
        async def metrics_endpoint():
            """指標端點"""
            return metrics.get_stats()

    # 註冊工具
    _register_tools(server, config)

    # 設置生命週期
    server.app.router.lifespan_context = lifespan

    _app_instance = server
    return server


def _register_tools(server: MCPServer, config) -> None:
    """
    註冊工具到 MCP Server

    Args:
        server: MCP Server 實例
        config: 配置實例
    """
    registry = get_registry()

    # 註冊 Task Analyzer 工具
    task_analyzer = TaskAnalyzerTool()
    registry.register(task_analyzer)
    server.register_tool(
        name=task_analyzer.name,
        description=task_analyzer.description,
        input_schema=task_analyzer.input_schema,
        handler=task_analyzer.execute,
    )

    # 註冊 File Tool
    file_tool_base_path = "/tmp"  # 可以從配置讀取
    file_tool = FileTool(base_path=file_tool_base_path)
    registry.register(file_tool)
    server.register_tool(
        name=file_tool.name,
        description=file_tool.description,
        input_schema=file_tool.input_schema,
        handler=file_tool.execute,
    )

    logger.info(f"Registered {len(registry.list_all())} tools")


def get_app() -> MCPServer:
    """
    獲取應用實例

    Returns:
        MCPServer: MCP Server 實例
    """
    if _app_instance is None:
        return create_app()
    return _app_instance


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="MCP Server")
    parser.add_argument("--host", type=str, default=None, help="服務器主機地址")
    parser.add_argument("--port", type=int, default=None, help="服務器端口")
    parser.add_argument(
        "--reload", action="store_true", help="啟用自動重載（開發模式）"
    )
    parser.add_argument("--config", type=str, default=None, help="配置文件路徑")

    args = parser.parse_args()

    # 獲取配置
    config = get_config()

    # 命令行參數覆蓋配置
    host = args.host or config.host
    port = args.port or config.port

    # 創建應用
    server = create_app(config)
    app = server.get_fastapi_app()

    # 啟動服務器
    logger.info(f"Starting MCP Server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=args.reload,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
