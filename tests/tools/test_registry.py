# 代碼功能說明: 工具註冊表測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊表測試"""

from __future__ import annotations

import pytest

from tools.base import BaseTool, ToolInput, ToolOutput
from tools.registry import ToolRegistry, get_tool_registry
from tools.utils.errors import ToolNotFoundError


class MockTool(BaseTool[ToolInput, ToolOutput]):
    """模擬工具"""

    def __init__(self, name: str = "mock_tool"):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "Mock tool"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, input_data: ToolInput) -> ToolOutput:
        return ToolOutput()


class TestToolRegistry:
    """工具註冊表測試"""

    def test_register_tool(self):
        """測試註冊工具"""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        assert "test_tool" in registry.list_tools()

    def test_register_duplicate_tool(self):
        """測試註冊重複工具"""
        registry = ToolRegistry()
        tool1 = MockTool("test_tool")
        tool2 = MockTool("test_tool")
        registry.register(tool1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(tool2)

    def test_get_tool(self):
        """測試獲取工具"""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        retrieved = registry.get_tool("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"

    def test_get_tool_not_found(self):
        """測試獲取不存在的工具"""
        registry = ToolRegistry()
        result = registry.get_tool("nonexistent")
        assert result is None

    def test_get_tool_or_raise_found(self):
        """測試獲取工具或拋出異常（工具存在）"""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        retrieved = registry.get_tool_or_raise("test_tool")
        assert retrieved.name == "test_tool"

    def test_get_tool_or_raise_not_found(self):
        """測試獲取工具或拋出異常（工具不存在）"""
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError):
            registry.get_tool_or_raise("nonexistent")

    def test_list_tools(self):
        """測試列出所有工具"""
        registry = ToolRegistry()
        tool1 = MockTool("tool1")
        tool2 = MockTool("tool2")
        registry.register(tool1)
        registry.register(tool2)
        tools = registry.list_tools()
        assert "tool1" in tools
        assert "tool2" in tools
        assert len(tools) == 2

    def test_list_tools_with_info(self):
        """測試列出工具詳細信息"""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        tools_info = registry.list_tools_with_info()
        assert len(tools_info) == 1
        assert tools_info[0]["name"] == "test_tool"
        assert tools_info[0]["description"] == "Mock tool"
        assert tools_info[0]["version"] == "1.0.0"

    def test_unregister_tool(self):
        """測試取消註冊工具"""
        registry = ToolRegistry()
        tool = MockTool("test_tool")
        registry.register(tool)
        assert registry.unregister("test_tool") is True
        assert "test_tool" not in registry.list_tools()

    def test_unregister_nonexistent_tool(self):
        """測試取消註冊不存在的工具"""
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_clear(self):
        """測試清空註冊表"""
        registry = ToolRegistry()
        tool1 = MockTool("tool1")
        tool2 = MockTool("tool2")
        registry.register(tool1)
        registry.register(tool2)
        registry.clear()
        assert len(registry.list_tools()) == 0

    def test_get_tool_registry_singleton(self):
        """測試獲取工具註冊表單例"""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()
        assert registry1 is registry2
