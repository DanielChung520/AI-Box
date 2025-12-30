# 代碼功能說明: 工具註冊表
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊表

管理所有工具的註冊、查詢和註銷。
"""

from __future__ import annotations

from threading import Lock
from typing import Dict, List, Optional

import structlog

from tools.base import BaseTool
from tools.utils.errors import ToolNotFoundError

logger = structlog.get_logger(__name__)


class ToolRegistry:
    """工具註冊表

    負責管理所有工具，支持動態註冊和查詢。
    """

    def __init__(self) -> None:
        """初始化工具註冊表"""
        self._tools: Dict[str, BaseTool] = {}
        self._lock = Lock()

    def register(self, tool: BaseTool) -> None:
        """
        註冊工具

        Args:
            tool: 工具實例

        Raises:
            ValueError: 如果工具名稱已存在
        """
        with self._lock:
            if tool.name in self._tools:
                raise ValueError(f"Tool '{tool.name}' already registered")
            self._tools[tool.name] = tool
            logger.info("tool_registered", tool_name=tool.name, version=tool.version)

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        獲取工具

        Args:
            name: 工具名稱

        Returns:
            工具實例，如果不存在返回 None
        """
        with self._lock:
            return self._tools.get(name)

    def get_tool_or_raise(self, name: str) -> BaseTool:
        """
        獲取工具（如果不存在則拋出異常）

        Args:
            name: 工具名稱

        Returns:
            工具實例

        Raises:
            ToolNotFoundError: 如果工具不存在
        """
        tool = self.get_tool(name)
        if tool is None:
            raise ToolNotFoundError(name)
        return tool

    def list_tools(self) -> List[str]:
        """
        列出所有工具名稱

        Returns:
            工具名稱列表
        """
        with self._lock:
            return list(self._tools.keys())

    def list_tools_with_info(self) -> List[Dict[str, str]]:
        """
        列出所有工具的詳細信息

        Returns:
            工具信息列表，每個元素包含 name, description, version
        """
        with self._lock:
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "version": tool.version,
                }
                for tool in self._tools.values()
            ]

    def unregister(self, name: str) -> bool:
        """
        取消註冊工具

        Args:
            name: 工具名稱

        Returns:
            是否成功取消註冊
        """
        with self._lock:
            if name in self._tools:
                del self._tools[name]
                logger.info("tool_unregistered", tool_name=name)
                return True
            return False

    def clear(self) -> None:
        """清空所有工具註冊"""
        with self._lock:
            self._tools.clear()
            logger.info("tool_registry_cleared")


# 全局工具註冊表實例（單例模式）
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    獲取工具註冊表實例（單例模式）

    Returns:
        ToolRegistry 實例
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry
