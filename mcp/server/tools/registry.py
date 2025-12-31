# 代碼功能說明: MCP Server 工具註冊表
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""MCP Server 工具註冊表模組"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具註冊表（擴展版）"""

    def __init__(self):
        """初始化工具註冊表"""
        self.tools: Dict[str, BaseTool] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}  # 工具元數據

    def register(
        self,
        tool: BaseTool,
        tool_type: str = "internal",  # "internal" 或 "external"
        source: Optional[str] = None,  # 外部工具來源
    ) -> None:
        """
        註冊工具（擴展版）

        Args:
            tool: 工具實例
            tool_type: 工具類型（"internal" 或 "external"）
            source: 工具來源（外部工具需要）
        """
        if tool.name in self.tools:
            logger.warning(f"Tool '{tool.name}' already registered, overwriting")
        self.tools[tool.name] = tool
        self.tool_metadata[tool.name] = {
            "type": tool_type,
            "source": source,
            "registered_at": datetime.now().isoformat(),
            "call_count": 0,
            "success_count": 0,
            "failure_count": 0,
        }
        logger.info(f"Registered {tool_type} tool: {tool.name}")

    def record_tool_call(self, name: str, success: bool) -> None:
        """
        記錄工具調用

        Args:
            name: 工具名稱
            success: 是否成功
        """
        if name in self.tool_metadata:
            self.tool_metadata[name]["call_count"] += 1
            if success:
                self.tool_metadata[name]["success_count"] += 1
            else:
                self.tool_metadata[name]["failure_count"] += 1

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

    def get_tool_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        獲取工具統計信息

        Args:
            name: 工具名稱

        Returns:
            Optional[Dict[str, Any]]: 統計信息，如果工具不存在則返回 None
        """
        return self.tool_metadata.get(name)

    def list_by_type(self, tool_type: str) -> List[BaseTool]:
        """
        按類型列出工具

        Args:
            tool_type: 工具類型（"internal" 或 "external"）

        Returns:
            List[BaseTool]: 工具列表
        """
        return [
            tool
            for name, tool in self.tools.items()
            if self.tool_metadata.get(name, {}).get("type") == tool_type
        ]


# 全局工具註冊表實例
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """
    獲取全局工具註冊表實例

    Returns:
        ToolRegistry: 工具註冊表實例
    """
    return _registry
