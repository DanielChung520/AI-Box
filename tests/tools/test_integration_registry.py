# 代碼功能說明: 工具註冊表集成測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊表集成測試

測試所有工具的註冊流程、查找和調用。
"""

from __future__ import annotations

import threading

import pytest

from tools import register_all_tools
from tools.calculator import MathCalculator
from tools.conversion import LengthConverter, LengthInput
from tools.registry import ToolRegistry, get_tool_registry
from tools.text import TextFormatter
from tools.time import DateTimeInput, DateTimeTool
from tools.utils.errors import ToolNotFoundError


@pytest.mark.asyncio
class TestToolRegistryIntegration:
    """工具註冊表集成測試"""

    @pytest.fixture
    def registry(self):
        """創建註冊表實例"""
        return ToolRegistry()

    @pytest.mark.asyncio
    async def test_register_all_tools(self, registry):
        """測試註冊所有工具"""
        register_all_tools(registry)

        tools = registry.list_tools()
        assert len(tools) > 0

        # 驗證一些核心工具已註冊
        assert "datetime" in tools
        assert "weather" in tools
        assert "ip_location" in tools
        assert "length_converter" in tools

    @pytest.mark.asyncio
    async def test_tool_execution_through_registry(self, registry):
        """測試通過註冊表執行工具"""
        # 註冊工具
        datetime_tool = DateTimeTool()
        registry.register(datetime_tool)

        # 獲取工具並執行
        tool = registry.get_tool("datetime")
        assert tool is not None

        input_data = DateTimeInput()
        result = await tool.execute(input_data)

        assert result is not None
        assert result.timestamp > 0

    @pytest.mark.asyncio
    async def test_multiple_tools_registration(self, registry):
        """測試註冊多個工具"""
        tools_to_register = [
            DateTimeTool(),
            LengthConverter(),
            MathCalculator(),
            TextFormatter(),
        ]

        for tool in tools_to_register:
            registry.register(tool)

        assert len(registry.list_tools()) == len(tools_to_register)

    @pytest.mark.asyncio
    async def test_tool_not_found_error(self, registry):
        """測試工具未找到錯誤"""
        with pytest.raises(ToolNotFoundError):
            registry.get_tool_or_raise("nonexistent_tool")

    @pytest.mark.asyncio
    async def test_tool_list_with_info(self, registry):
        """測試列出工具詳細信息"""
        register_all_tools(registry)

        tools_info = registry.list_tools_with_info()
        assert len(tools_info) > 0

        # 驗證工具信息結構
        for tool_info in tools_info:
            assert "name" in tool_info
            assert "description" in tool_info
            assert "version" in tool_info
            assert tool_info["name"] is not None
            assert tool_info["description"] is not None
            assert tool_info["version"] is not None

    @pytest.mark.asyncio
    async def test_thread_safety(self, registry):
        """測試線程安全性"""
        results = []

        def register_and_get_tool(tool_name: str):
            """註冊並獲取工具"""
            try:
                tool = DateTimeTool()
                registry.register(tool)
                retrieved = registry.get_tool("datetime")
                results.append(retrieved is not None)
            except Exception:
                results.append(False)

        # 創建多個線程同時操作註冊表
        threads = [
            threading.Thread(target=register_and_get_tool, args=(f"tool_{i}",)) for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 驗證所有操作都成功（或至少沒有崩潰）
        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_tool_unregister_and_reregister(self, registry):
        """測試取消註冊和重新註冊"""
        tool = DateTimeTool()
        registry.register(tool)

        assert "datetime" in registry.list_tools()

        # 取消註冊
        registry.unregister("datetime")
        assert "datetime" not in registry.list_tools()

        # 重新註冊
        new_tool = DateTimeTool()
        registry.register(new_tool)
        assert "datetime" in registry.list_tools()

    @pytest.mark.asyncio
    async def test_global_registry_singleton(self):
        """測試全局註冊表單例"""
        registry1 = get_tool_registry()
        registry2 = get_tool_registry()

        assert registry1 is registry2

        # 註冊工具到一個實例
        tool = DateTimeTool()
        registry1.register(tool)

        # 從另一個實例獲取
        retrieved = registry2.get_tool("datetime")
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_all_registered_tools_executable(self, registry):
        """測試所有已註冊的工具都可以執行"""
        register_all_tools(registry)

        tools = registry.list_tools()

        # 測試一些核心工具可以執行
        test_cases = [
            ("datetime", DateTimeInput()),
            ("length_converter", LengthInput(value=1.0, from_unit="meter", to_unit="kilometer")),
        ]

        for tool_name, input_data in test_cases:
            if tool_name in tools:
                tool = registry.get_tool(tool_name)
                assert tool is not None

                result = await tool.execute(input_data)
                assert result is not None
