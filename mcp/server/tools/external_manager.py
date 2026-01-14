# 代碼功能說明: 外部 MCP 工具管理器
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-31

"""外部 MCP 工具管理器模組"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from mcp.server.server import MCPServer
from mcp.server.tools.external_tool import ExternalMCPTool
from mcp.server.tools.registry import get_registry

logger = logging.getLogger(__name__)


class ExternalToolManager:
    """外部 MCP 工具管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化外部工具管理器

        Args:
            config_path: 配置文件路徑
        """
        self.config_path = config_path or "external_mcp_tools.yaml"
        self.external_tool_configs: List[Dict[str, Any]] = []
        self.registered_tools: Dict[str, ExternalMCPTool] = {}
        self.refresh_task: Optional[asyncio.Task] = None
        self.refresh_interval = 3600  # 1 小時

    def load_config(self) -> List[Dict[str, Any]]:
        """
        加載外部工具配置（優先從 ArangoDB 讀取，回退到 YAML 文件）

        Returns:
            List[Dict[str, Any]]: 工具配置列表
        """
        # 優先從 ArangoDB 讀取配置
        try:
            from services.api.services.config_store_service import ConfigStoreService

            config_service = ConfigStoreService()
            config = config_service.get_config("mcp.external_services", tenant_id=None)

            if config and config.config_data:
                # 從 ArangoDB 讀取配置
                external_services = config.config_data.get("external_services", [])

                # 過濾啟用的服務
                enabled_services = [
                    service for service in external_services if service.get("enabled", True)
                ]

                # 解析環境變量引用
                resolved_services = []
                for service in enabled_services:
                    resolved_service = self._resolve_env_variables(service)
                    resolved_services.append(resolved_service)

                self.external_tool_configs = resolved_services
                logger.info(
                    f"Loaded {len(resolved_services)} external service configurations from ArangoDB"
                )
                return resolved_services
        except Exception as e:
            logger.warning(f"Failed to load config from ArangoDB: {e}, falling back to YAML file")

        # 回退到 YAML 文件（向後兼容）
        return self._load_config_from_yaml()

    def _load_config_from_yaml(self) -> List[Dict[str, Any]]:
        """從 YAML 文件加載配置（向後兼容）"""
        config_file = Path(self.config_path)

        if not config_file.exists():
            logger.warning(f"External tools config file not found: {self.config_path}")
            return []

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                self.external_tool_configs = config.get("external_tools", [])
                logger.info(
                    f"Loaded {len(self.external_tool_configs)} external tool configurations from YAML"
                )
                return self.external_tool_configs
        except Exception as e:
            logger.error(f"Failed to load external tools config: {e}")
            return []

    def _resolve_env_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析配置中的環境變量引用（如 ${GLAMA_OFFICE_API_KEY}）

        Args:
            config: 配置字典

        Returns:
            解析後的配置字典
        """
        import os
        import re

        def resolve_value(value: Any) -> Any:
            if isinstance(value, str):
                # 匹配 ${VAR_NAME} 格式
                pattern = r"\$\{([^}]+)\}"
                matches = re.findall(pattern, value)

                for var_name in matches:
                    env_value = os.getenv(var_name)
                    if env_value:
                        value = value.replace(f"${{{var_name}}}", env_value)
                    else:
                        logger.warning(
                            f"Environment variable {var_name} not found in config {config.get('name', 'unknown')}"
                        )

                return value
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value

        return resolve_value(config)

    async def discover_tools(self, mcp_endpoint: str) -> List[Dict[str, Any]]:
        """
        從外部 MCP Server 發現工具

        Args:
            mcp_endpoint: MCP Server 端點

        Returns:
            List[Dict[str, Any]]: 工具列表
        """
        try:
            from mcp.client.client import MCPClient

            client = MCPClient(endpoint=mcp_endpoint)
            await client.initialize()
            tools = await client.list_tools()
            await client.close()

            # 转换为字典列表
            result: List[Dict[str, Any]] = []
            for tool in tools:
                if hasattr(tool, "model_dump"):
                    # MCPTool 是 BaseModel，有 model_dump 方法
                    result.append(tool.model_dump())  # type: ignore[attr-defined]
                elif isinstance(tool, dict):
                    result.append(tool)
                else:
                    # 如果 tool 是对象，尝试转换为字典
                    result.append(dict(tool) if hasattr(tool, "__dict__") else {"name": str(tool)})
            return result
        except Exception as e:
            logger.error(f"Failed to discover tools from {mcp_endpoint}: {e}")
            return []

    async def register_external_tool(
        self, tool_config: Dict[str, Any], server: Optional[MCPServer] = None
    ) -> bool:
        """
        註冊外部工具

        Args:
            tool_config: 工具配置（從 ArangoDB 或 YAML 文件讀取）
            server: MCP Server 實例（可選）

        Returns:
            bool: 是否成功註冊
        """
        try:
            # 處理從 ArangoDB 讀取的配置格式（可能沒有 input_schema，需要自動發現）
            input_schema = tool_config.get("input_schema")
            if not input_schema:
                # 如果沒有 input_schema，使用默認 schema（將在工具發現時自動更新）
                input_schema = {
                    "type": "object",
                    "properties": {},
                    "description": "Schema will be auto-discovered from MCP Server",
                }

            # 創建外部工具代理
            external_tool = ExternalMCPTool(
                name=tool_config["name"],
                description=tool_config.get("description", ""),
                input_schema=input_schema,
                mcp_endpoint=tool_config["mcp_endpoint"],
                tool_name_on_server=tool_config.get("tool_name_on_server"),
                auth_config=tool_config.get("auth_config", {}),
                proxy_endpoint=tool_config.get("proxy_endpoint"),  # Gateway 代理端點
                proxy_config=tool_config.get("proxy_config", {}),  # 代理配置
            )

            # 如果啟用了自動發現，先發現工具並更新 schema
            if tool_config.get("auto_discover", True):
                try:
                    discovered_tools = await self.discover_tools(tool_config["mcp_endpoint"])
                    if discovered_tools:
                        # 找到對應的工具並更新 schema
                        tool_name_on_server = tool_config.get(
                            "tool_name_on_server", tool_config["name"]
                        )
                        for discovered_tool in discovered_tools:
                            if discovered_tool.get("name") == tool_name_on_server:
                                # 更新 input_schema
                                if "inputSchema" in discovered_tool:
                                    external_tool.input_schema = discovered_tool["inputSchema"]
                                elif "input_schema" in discovered_tool:
                                    external_tool.input_schema = discovered_tool["input_schema"]
                                break
                except Exception as e:
                    logger.warning(
                        f"Failed to auto-discover tools for {tool_config['name']}: {e}, using default schema"
                    )

            # 驗證連接
            if await external_tool.verify_connection():
                # 註冊到工具註冊表
                registry = get_registry()
                registry.register(
                    external_tool,
                    tool_type="external",
                    source=tool_config["mcp_endpoint"],
                )

                # 註冊到 MCP Server
                if server:
                    server.register_tool(
                        name=external_tool.name,
                        description=external_tool.description,
                        input_schema=external_tool.input_schema,
                        handler=external_tool.execute,
                    )

                self.registered_tools[external_tool.name] = external_tool
                logger.info(f"Registered external tool: {external_tool.name}")
                return True
            else:
                logger.warning(
                    f"Failed to verify connection for external tool: {tool_config['name']}"
                )
                return False

        except Exception as e:
            logger.error(f"Failed to register external tool {tool_config.get('name')}: {e}")
            return False

    async def register_all_external_tools(self, server: Optional[MCPServer] = None) -> int:
        """
        註冊所有外部工具

        Args:
            server: MCP Server 實例（可選）

        Returns:
            int: 成功註冊的工具數量
        """
        # 加載配置
        configs = self.load_config()

        # 註冊所有工具
        success_count = 0
        for tool_config in configs:
            if await self.register_external_tool(tool_config, server):
                success_count += 1

        logger.info(f"Registered {success_count}/{len(configs)} external tools")
        return success_count

    async def unregister_external_tool(self, tool_name: str) -> bool:
        """
        取消註冊外部工具

        Args:
            tool_name: 工具名稱

        Returns:
            bool: 是否成功取消註冊
        """
        if tool_name not in self.registered_tools:
            return False

        try:
            tool = self.registered_tools[tool_name]
            await tool.close()

            registry = get_registry()
            registry.unregister(tool_name)

            del self.registered_tools[tool_name]
            logger.info(f"Unregistered external tool: {tool_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister external tool {tool_name}: {e}")
            return False

    async def refresh_external_tools(self) -> Dict[str, Any]:
        """
        刷新所有外部工具

        Returns:
            Dict[str, Any]: 刷新結果統計
        """
        stats = {
            "total": len(self.registered_tools),
            "refreshed": 0,
            "failed": 0,
            "new_tools": 0,
            "removed_tools": 0,
        }

        for tool_name, tool in list(self.registered_tools.items()):
            try:
                # 檢查工具健康狀態
                health = await tool.health_check()
                if health["status"] != "healthy":
                    logger.warning(f"External tool '{tool_name}' is unhealthy")
                    stats["failed"] += 1
                else:
                    stats["refreshed"] += 1
            except Exception as e:
                logger.error(f"Failed to refresh external tool '{tool_name}': {e}")
                stats["failed"] += 1

        # 檢查配置中的新工具
        configs = self.load_config()
        config_tool_names = {cfg["name"] for cfg in configs}
        registered_tool_names = set(self.registered_tools.keys())

        # 發現新工具
        new_tools = config_tool_names - registered_tool_names
        for tool_name in new_tools:
            tool_config = next((cfg for cfg in configs if cfg["name"] == tool_name), None)
            if tool_config:
                if await self.register_external_tool(tool_config):
                    stats["new_tools"] += 1

        # 發現已移除的工具
        removed_tools = registered_tool_names - config_tool_names
        for tool_name in removed_tools:
            if await self.unregister_external_tool(tool_name):
                stats["removed_tools"] += 1

        logger.info(f"Refreshed external tools: {stats}")
        return stats

    async def start_refresh_loop(self) -> None:
        """啟動定期刷新循環"""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                await self.refresh_external_tools()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in external tools refresh loop: {e}")

    def stop_refresh_loop(self) -> None:
        """停止定期刷新循環"""
        if self.refresh_task:
            self.refresh_task.cancel()

    async def close(self) -> None:
        """關閉所有外部工具連接"""
        for tool in self.registered_tools.values():
            try:
                await tool.close()
            except Exception as e:
                logger.error(f"Failed to close external tool: {e}")

        self.registered_tools.clear()
        self.stop_refresh_loop()


# 全局外部工具管理器實例
_external_tool_manager: Optional[ExternalToolManager] = None


def get_external_tool_manager() -> ExternalToolManager:
    """
    獲取全局外部工具管理器實例

    Returns:
        ExternalToolManager: 外部工具管理器實例
    """
    global _external_tool_manager
    if _external_tool_manager is None:
        _external_tool_manager = ExternalToolManager()
    return _external_tool_manager
