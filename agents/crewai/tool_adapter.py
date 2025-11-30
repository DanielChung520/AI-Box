# 代碼功能說明: Tool Registry 適配層
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""將 Tool Registry 中的工具轉換為 CrewAI 可用的工具格式。"""

import logging
from typing import Any, Callable, Dict, List, Optional

from crewai_tools import BaseTool
from agents.infra.tools.registry import ToolRegistry, Tool

logger = logging.getLogger(__name__)


class ToolAdapter:
    """工具適配器，將 Tool Registry 工具轉換為 CrewAI 工具。"""

    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """
        初始化工具適配器。

        Args:
            tool_registry: Tool Registry 實例（可選）
        """
        self._tool_registry = tool_registry or ToolRegistry()
        self._crewai_tools: Dict[str, BaseTool] = {}

    def adapt_tool(self, tool: Tool) -> Optional[BaseTool]:
        """
        將 Tool Registry 工具轉換為 CrewAI 工具。

        Args:
            tool: Tool Registry 工具

        Returns:
            CrewAI 工具，如果轉換失敗則返回 None
        """
        try:
            # 創建 CrewAI 工具包裝器
            crewai_tool = CrewAIToolWrapper(
                name=tool.name,
                description=tool.description,
                handler=tool.handler,
                config=tool.config,
            )
            self._crewai_tools[tool.name] = crewai_tool
            logger.info(f"Adapted tool '{tool.name}' for CrewAI")
            return crewai_tool
        except Exception as exc:
            logger.error(f"Failed to adapt tool '{tool.name}': {exc}")
            return None

    def get_tools_for_agent(
        self,
        tool_names: Optional[List[str]] = None,
    ) -> List[BaseTool]:
        """
        獲取 Agent 所需的工具列表。

        Args:
            tool_names: 工具名稱列表（可選，如果為 None 則返回所有工具）

        Returns:
            CrewAI 工具列表
        """
        tools = []

        if tool_names:
            # 獲取指定的工具
            for tool_name in tool_names:
                if tool_name in self._crewai_tools:
                    tools.append(self._crewai_tools[tool_name])
                else:
                    # 嘗試從 Tool Registry 獲取並適配
                    tool = self._tool_registry.get(tool_name)
                    if tool:
                        adapted = self.adapt_tool(tool)
                        if adapted:
                            tools.append(adapted)
                    else:
                        logger.warning(f"Tool '{tool_name}' not found in registry")
        else:
            # 獲取所有啟用的工具
            all_tools = self._tool_registry.list_tools(enabled_only=True)
            for tool in all_tools:
                if tool.name not in self._crewai_tools:
                    adapted = self.adapt_tool(tool)
                    if adapted:
                        tools.append(adapted)
                else:
                    tools.append(self._crewai_tools[tool.name])

        return tools

    def discover_tools(self, query: str) -> List[BaseTool]:
        """
        發現工具（基於名稱或描述搜索）。

        Args:
            query: 搜索查詢

        Returns:
            匹配的 CrewAI 工具列表
        """
        matched_tools = self._tool_registry.discover(query)
        tools = []

        for tool in matched_tools:
            if tool.name not in self._crewai_tools:
                adapted = self.adapt_tool(tool)
                if adapted:
                    tools.append(adapted)
            else:
                tools.append(self._crewai_tools[tool.name])

        return tools


class CrewAIToolWrapper(BaseTool):
    """CrewAI 工具包裝器。"""

    name: str
    description: str
    _handler: Optional[Callable[..., Any]]
    _config: Dict[str, Any]

    def __init__(
        self,
        name: str,
        description: str,
        handler: Optional[Callable[..., Any]],
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 CrewAI 工具包裝器。

        Args:
            name: 工具名稱
            description: 工具描述
            handler: 工具處理函數
            config: 工具配置
        """
        super().__init__()
        self.name = name
        self.description = description
        self._handler = handler
        self._config = config or {}

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """
        執行工具（同步）。

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            工具執行結果
        """
        if self._handler is None:
            raise ValueError(f"Tool '{self.name}' has no handler")

        try:
            # 合併配置和參數
            merged_kwargs = {**self._config, **kwargs}
            result = self._handler(*args, **merged_kwargs)
            logger.debug(f"Tool '{self.name}' executed successfully")
            return result
        except Exception as exc:
            logger.error(f"Tool '{self.name}' execution failed: {exc}")
            raise

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """
        執行工具（異步）。

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            工具執行結果
        """
        # 如果處理函數是異步的，直接調用
        import inspect

        if self._handler is not None and inspect.iscoroutinefunction(self._handler):
            merged_kwargs = {**self._config, **kwargs}
            return await self._handler(*args, **merged_kwargs)
        else:
            # 否則使用同步版本
            return self._run(*args, **kwargs)
