# 代碼功能說明: 文本格式化工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本格式化工具測試"""

from __future__ import annotations

import pytest

from tools.text import TextFormatter, TextFormatterInput, TextFormatterOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestTextFormatter:
    """文本格式化工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return TextFormatter()

    @pytest.mark.asyncio
    async def test_uppercase(self, tool):
        """測試轉大寫"""
        input_data = TextFormatterInput(text="hello world", operation="uppercase")
        result = await tool.execute(input_data)

        assert isinstance(result, TextFormatterOutput)
        assert result.formatted_text == "HELLO WORLD"

    @pytest.mark.asyncio
    async def test_lowercase(self, tool):
        """測試轉小寫"""
        input_data = TextFormatterInput(text="HELLO WORLD", operation="lowercase")
        result = await tool.execute(input_data)

        assert result.formatted_text == "hello world"

    @pytest.mark.asyncio
    async def test_title(self, tool):
        """測試標題格式"""
        input_data = TextFormatterInput(text="hello world", operation="title")
        result = await tool.execute(input_data)

        assert result.formatted_text == "Hello World"

    @pytest.mark.asyncio
    async def test_strip(self, tool):
        """測試去除首尾空白"""
        input_data = TextFormatterInput(text="  hello world  ", operation="strip")
        result = await tool.execute(input_data)

        assert result.formatted_text == "hello world"

    @pytest.mark.asyncio
    async def test_invalid_operation(self, tool):
        """測試無效操作"""
        input_data = TextFormatterInput(text="hello", operation="invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
