# 代碼功能說明: 文本清理工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本清理工具測試"""

from __future__ import annotations

import pytest

from tools.text import TextCleaner, TextCleanerInput, TextCleanerOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestTextCleaner:
    """文本清理工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return TextCleaner()

    @pytest.mark.asyncio
    async def test_remove_whitespace(self, tool):
        """測試去除空白字符"""
        input_data = TextCleanerInput(text="hello world", operation="remove_whitespace")
        result = await tool.execute(input_data)

        assert isinstance(result, TextCleanerOutput)
        assert result.cleaned_text == "helloworld"

    @pytest.mark.asyncio
    async def test_remove_html_tags(self, tool):
        """測試去除 HTML 標籤"""
        input_data = TextCleanerInput(
            text="<p>Hello <b>World</b></p>", operation="remove_html_tags"
        )
        result = await tool.execute(input_data)

        assert "Hello" in result.cleaned_text
        assert "World" in result.cleaned_text
        assert "<" not in result.cleaned_text

    @pytest.mark.asyncio
    async def test_normalize_whitespace(self, tool):
        """測試標準化空白字符"""
        input_data = TextCleanerInput(text="hello    world", operation="normalize_whitespace")
        result = await tool.execute(input_data)

        assert result.cleaned_text == "hello world"

    @pytest.mark.asyncio
    async def test_invalid_operation(self, tool):
        """測試無效操作"""
        input_data = TextCleanerInput(text="hello", operation="invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)
