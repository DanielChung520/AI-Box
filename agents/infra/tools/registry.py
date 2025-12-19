# 代碼功能說明: Tool Registry 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Tool Registry - 實現工具註冊、發現和管理功能"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from agents.services.resource_controller import get_resource_controller

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """工具類型枚舉"""

    REST = "rest"  # REST API
    SQL = "sql"  # SQL 查詢
    CUSTOM = "custom"  # 自定義工具
    MCP = "mcp"  # MCP API


@dataclass
class Tool:
    """工具定義"""

    name: str
    description: str
    tool_type: ToolType
    handler: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: datetime = field(default_factory=datetime.now)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type.value,
            "config": self.config,
            "metadata": self.metadata,
            "registered_at": self.registered_at.isoformat(),
            "enabled": self.enabled,
        }


class ToolRegistry:
    """工具註冊表"""

    def __init__(self):
        """初始化工具註冊表"""
        self._tools: Dict[str, Tool] = {}
        self._tools_by_type: Dict[ToolType, List[str]] = {tool_type: [] for tool_type in ToolType}
        # 資源訪問控制器
        self._resource_controller = get_resource_controller()

    def register(
        self,
        name: str,
        description: str,
        tool_type: ToolType,
        handler: Optional[Callable] = None,
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        註冊工具

        Args:
            name: 工具名稱
            description: 工具描述
            tool_type: 工具類型
            handler: 工具處理函數
            config: 工具配置
            metadata: 工具元數據

        Returns:
            是否成功註冊
        """
        try:
            if name in self._tools:
                logger.warning(f"Tool '{name}' already registered, updating...")

            tool = Tool(
                name=name,
                description=description,
                tool_type=tool_type,
                handler=handler,
                config=config or {},
                metadata=metadata or {},
            )

            self._tools[name] = tool
            self._tools_by_type[tool_type].append(name)

            logger.info(f"Registered tool: {name} (type: {tool_type.value})")
            return True
        except Exception as e:
            logger.error(f"Failed to register tool '{name}': {e}")
            return False

    def unregister(self, name: str) -> bool:
        """
        取消註冊工具

        Args:
            name: 工具名稱

        Returns:
            是否成功取消註冊
        """
        try:
            if name not in self._tools:
                logger.warning(f"Tool '{name}' not found")
                return False

            tool = self._tools[name]
            self._tools_by_type[tool.tool_type].remove(name)
            del self._tools[name]

            logger.info(f"Unregistered tool: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister tool '{name}': {e}")
            return False

    def get(self, name: str) -> Optional[Tool]:
        """
        獲取工具

        Args:
            name: 工具名稱

        Returns:
            工具對象，如果不存在則返回 None
        """
        return self._tools.get(name)

    def list_tools(
        self,
        tool_type: Optional[ToolType] = None,
        enabled_only: bool = True,
    ) -> List[Tool]:
        """
        列出工具

        Args:
            tool_type: 工具類型過濾器
            enabled_only: 是否只返回啟用的工具

        Returns:
            工具列表
        """
        tools = []

        if tool_type:
            tool_names = self._tools_by_type.get(tool_type, [])
            tools = [self._tools[name] for name in tool_names if name in self._tools]
        else:
            tools = list(self._tools.values())

        if enabled_only:
            tools = [tool for tool in tools if tool.enabled]

        return tools

    def discover(
        self,
        query: str,
        tool_type: Optional[ToolType] = None,
    ) -> List[Tool]:
        """
        發現工具（基於名稱或描述搜索）

        Args:
            query: 搜索查詢
            query_lower = query.lower()
            tool_type: 工具類型過濾器

        Returns:
            匹配的工具列表
        """
        query_lower = query.lower()
        tools = self.list_tools(tool_type=tool_type, enabled_only=True)

        matched_tools = []
        for tool in tools:
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                matched_tools.append(tool)

        return matched_tools

    def enable(self, name: str) -> bool:
        """
        啟用工具

        Args:
            name: 工具名稱

        Returns:
            是否成功啟用
        """
        tool = self.get(name)
        if tool:
            tool.enabled = True
            logger.info(f"Enabled tool: {name}")
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        禁用工具

        Args:
            name: 工具名稱

        Returns:
            是否成功禁用
        """
        tool = self.get(name)
        if tool:
            tool.enabled = False
            logger.info(f"Disabled tool: {name}")
            return True
        return False

    def execute(
        self,
        name: str,
        *args,
        agent_id: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        執行工具

        Args:
            name: 工具名稱
            *args: 位置參數
            agent_id: Agent ID（可選，用於權限檢查）
            **kwargs: 關鍵字參數

        Returns:
            工具執行結果
        """
        # 資源訪問權限檢查
        if agent_id:
            if not self._resource_controller.check_tool_access(agent_id, name):
                logger.warning(
                    f"Agent '{agent_id}' does not have permission to execute tool '{name}'"
                )
                raise PermissionError(
                    f"Agent '{agent_id}' does not have permission to execute tool '{name}'"
                )

        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")

        if not tool.enabled:
            raise ValueError(f"Tool '{name}' is disabled")

        if not tool.handler:
            raise ValueError(f"Tool '{name}' has no handler")

        logger.info(f"Executing tool: {name}")
        try:
            result = tool.handler(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"Failed to execute tool '{name}': {e}")
            raise

    def get_tool_count(self, tool_type: Optional[ToolType] = None) -> int:
        """
        獲取工具數量

        Args:
            tool_type: 工具類型過濾器

        Returns:
            工具數量
        """
        if tool_type:
            return len(self._tools_by_type.get(tool_type, []))
        return len(self._tools)
