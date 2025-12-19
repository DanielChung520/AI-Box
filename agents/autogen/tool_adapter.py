# 代碼功能說明: Tool Registry 適配層（AutoGen）
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""將 Tool Registry 中的工具轉換為 AutoGen 可用的函數格式。"""

import logging
from typing import Any, Callable, Dict, List, Optional

from agents.infra.tools.registry import Tool, ToolRegistry

logger = logging.getLogger(__name__)


class AutoGenToolAdapter:
    """工具適配器，將 Tool Registry 工具轉換為 AutoGen 可用的函數。"""

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        初始化工具適配器。

        Args:
            tool_registry: Tool Registry 實例（可選）
        """
        self._tool_registry = tool_registry or ToolRegistry()
        self._autogen_tools: Dict[str, Callable] = {}

    def adapt_tool(self, tool: Tool) -> Optional[Callable]:
        """
        將 Tool Registry 工具轉換為 AutoGen 可用的函數。

        Args:
            tool: Tool Registry 工具

        Returns:
            AutoGen 可用的函數，如果轉換失敗則返回 None
        """
        try:
            if not tool.handler:
                logger.warning(f"Tool '{tool.name}' has no handler")
                return None

            # 確保 handler 不為 None（mypy 類型檢查）
            handler = tool.handler
            if handler is None:
                return None

            # 創建包裝函數
            def tool_wrapper(*args: Any, **kwargs: Any) -> Any:
                """工具包裝函數。"""
                try:
                    # 合併配置和參數
                    merged_kwargs = {**tool.config, **kwargs}
                    result = handler(*args, **merged_kwargs)
                    logger.debug(f"Tool '{tool.name}' executed successfully")
                    return result
                except Exception as exc:
                    logger.error(f"Tool '{tool.name}' execution failed: {exc}")
                    raise

            # 設置函數元數據
            tool_wrapper.__name__ = tool.name
            tool_wrapper.__doc__ = tool.description

            self._autogen_tools[tool.name] = tool_wrapper
            logger.info(f"Adapted tool '{tool.name}' for AutoGen")
            return tool_wrapper
        except Exception as exc:
            logger.error(f"Failed to adapt tool '{tool.name}': {exc}")
            return None

    def get_tools_for_agent(
        self,
        tool_names: Optional[List[str]] = None,
    ) -> Dict[str, Callable]:
        """
        獲取 Agent 所需的工具字典。

        Args:
            tool_names: 工具名稱列表（可選，如果為 None 則返回所有工具）

        Returns:
            AutoGen 工具字典，key 為工具名稱，value 為函數
        """
        tools = {}

        if tool_names:
            # 獲取指定的工具
            for tool_name in tool_names:
                if tool_name in self._autogen_tools:
                    tools[tool_name] = self._autogen_tools[tool_name]
                else:
                    # 嘗試從 Tool Registry 獲取並適配
                    tool = self._tool_registry.get(tool_name)
                    if tool:
                        adapted = self.adapt_tool(tool)
                        if adapted:
                            tools[tool_name] = adapted
                    else:
                        logger.warning(f"Tool '{tool_name}' not found in registry")
        else:
            # 獲取所有啟用的工具
            all_tools = self._tool_registry.list_tools(enabled_only=True)
            for tool in all_tools:
                if tool.name not in self._autogen_tools:
                    adapted = self.adapt_tool(tool)
                    if adapted:
                        tools[tool.name] = adapted
                else:
                    tools[tool.name] = self._autogen_tools[tool.name]

        return tools

    def discover_tools(self, query: str) -> Dict[str, Callable]:
        """
        發現工具（基於名稱或描述搜索）。

        Args:
            query: 搜索查詢

        Returns:
            匹配的 AutoGen 工具字典
        """
        matched_tools = self._tool_registry.discover(query)
        tools = {}

        for tool in matched_tools:
            if tool.name not in self._autogen_tools:
                adapted = self.adapt_tool(tool)
                if adapted:
                    tools[tool.name] = adapted
            else:
                tools[tool.name] = self._autogen_tools[tool.name]

        return tools

    def get_tool_descriptions(self) -> List[Dict[str, str]]:
        """
        獲取所有工具的描述列表（用於 Agent 系統提示）。

        Returns:
            工具描述列表
        """
        descriptions = []
        for tool_name, tool_func in self._autogen_tools.items():
            tool = self._tool_registry.get(tool_name)
            if tool:
                descriptions.append(
                    {
                        "name": tool_name,
                        "description": tool.description,
                        "doc": tool_func.__doc__ or tool.description,
                    }
                )
        return descriptions
