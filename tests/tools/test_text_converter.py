# 代碼功能說明: 文本轉換工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本轉換工具測試"""

from __future__ import annotations

import pytest

from tools.text import TextConverter, TextConverterInput, TextConverterOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestTextConverter:
    """文本轉換工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return TextConverter()

    @pytest.mark.asyncio
    async def test_markdown_to_html(self, tool):
        """測試 Markdown 轉 HTML"""
        markdown_text = "# Title\n\nThis is a paragraph."
        input_data = TextConverterInput(
            text=markdown_text, from_format="markdown", to_format="html"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert result.from_format == "markdown"
        assert result.to_format == "html"
        assert "<h1>Title</h1>" in result.converted_text
        assert "<p>This is a paragraph.</p>" in result.converted_text

    @pytest.mark.asyncio
    async def test_html_to_text(self, tool):
        """測試 HTML 轉純文本"""
        html_text = "<h1>Title</h1><p>This is a paragraph.</p>"
        input_data = TextConverterInput(text=html_text, from_format="html", to_format="plain")
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert result.from_format == "html"
        assert result.to_format == "plain"
        assert "Title" in result.converted_text
        assert "This is a paragraph" in result.converted_text

    @pytest.mark.asyncio
    async def test_text_to_html(self, tool):
        """測試純文本轉 HTML"""
        plain_text = "This is a line.\nThis is another line."
        input_data = TextConverterInput(text=plain_text, from_format="plain", to_format="html")
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert "<br>" in result.converted_text or "<p>" in result.converted_text

    @pytest.mark.asyncio
    async def test_same_format(self, tool):
        """測試相同格式轉換"""
        text = "This is a test."
        input_data = TextConverterInput(text=text, from_format="plain", to_format="plain")
        result = await tool.execute(input_data)

        assert result.converted_text == text

    @pytest.mark.asyncio
    async def test_invalid_format(self, tool):
        """測試無效格式"""
        input_data = TextConverterInput(text="test", from_format="invalid", to_format="html")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_markdown_list_to_html(self, tool):
        """測試 Markdown 列表轉 HTML"""
        markdown_text = "- Item 1\n- Item 2\n- Item 3"
        input_data = TextConverterInput(
            text=markdown_text, from_format="markdown", to_format="html"
        )
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert "<ul>" in result.converted_text
        assert "<li>Item 1</li>" in result.converted_text

    @pytest.mark.asyncio
    async def test_html_with_script_tags(self, tool):
        """測試包含 script 標籤的 HTML"""
        html_text = "<script>alert('test')</script><p>Content</p>"
        input_data = TextConverterInput(text=html_text, from_format="html", to_format="plain")
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert "alert" not in result.converted_text  # script 標籤應該被過濾
        assert "Content" in result.converted_text

    @pytest.mark.asyncio
    async def test_empty_text(self, tool):
        """測試空文本"""
        input_data = TextConverterInput(text="", from_format="plain", to_format="html")
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert result.converted_text is not None

    @pytest.mark.asyncio
    async def test_format_case_insensitive(self, tool):
        """測試格式大小寫不敏感"""
        input_data = TextConverterInput(text="# Title", from_format="MARKDOWN", to_format="HTML")
        result = await tool.execute(input_data)

        assert isinstance(result, TextConverterOutput)
        assert "<h1>Title</h1>" in result.converted_text
