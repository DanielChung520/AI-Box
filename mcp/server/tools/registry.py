# 代碼功能說明: MCP Server 工具註冊表
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Server 工具註冊表模組"""

import logging
from typing import Dict, List, Optional

from mcp.server.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具註冊表"""

    def __init__(self):
        """初始化工具註冊表"""
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        註冊工具

        Args:
            tool: 工具實例
        """
        if tool.name in self.tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> bool:
        """
        取消註冊工具

        Args:
            name: 工具名稱

        Returns:
            bool: 是否成功取消註冊
        """
        if name in self.tools:
            del self.tools[name]
            logger.info(f"Unregistered tool: {name}")
            return True
        return False

    def get(self, name: str) -> Optional[BaseTool]:
        """
        獲取工具

        Args:
            name: 工具名稱

        Returns:
            Optional[BaseTool]: 工具實例，如果不存在則返回 None
        """
        return self.tools.get(name)

    def list_all(self) -> List[BaseTool]:
        """
        列出所有工具

        Returns:
            List[BaseTool]: 工具列表
        """
        return list(self.tools.values())

    def get_tool_info_list(self) -> List[Dict]:
        """
        獲取所有工具信息列表

        Returns:
            List[Dict]: 工具信息列表
        """
        return [tool.get_info() for tool in self.tools.values()]


# 全局工具註冊表實例
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """
    獲取全局工具註冊表實例

    Returns:
        ToolRegistry: 工具註冊表實例
    """
    return _registry
