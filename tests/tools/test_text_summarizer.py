# 代碼功能說明: 文本摘要工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""文本摘要工具測試"""

from __future__ import annotations

import pytest

from tools.text import TextSummarizer, TextSummarizerInput, TextSummarizerOutput
from tools.utils.errors import ToolValidationError


@pytest.mark.asyncio
class TestTextSummarizer:
    """文本摘要工具測試"""

    @pytest.fixture
    def tool(self):
        """創建工具實例"""
        return TextSummarizer()

    @pytest.fixture
    def sample_text(self):
        """示例文本"""
        return (
            "Python is a high-level programming language. "
            "It is widely used for web development, data science, and automation. "
            "Python has a simple syntax that makes it easy to learn. "
            "Many developers prefer Python for its readability and versatility."
        )

    @pytest.mark.asyncio
    async def test_extract_keywords(self, tool, sample_text):
        """測試提取關鍵詞"""
        input_data = TextSummarizerInput(text=sample_text, operation="keywords", max_keywords=5)
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        assert result.operation == "keywords"
        assert result.keywords is not None
        assert len(result.keywords) <= 5
        assert isinstance(result.keywords, list)

    @pytest.mark.asyncio
    async def test_generate_summary(self, tool, sample_text):
        """測試生成摘要"""
        input_data = TextSummarizerInput(text=sample_text, operation="summary", summary_length=2)
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        assert result.operation == "summary"
        assert result.result is not None
        assert len(result.result) > 0

    @pytest.mark.asyncio
    async def test_calculate_stats(self, tool, sample_text):
        """測試計算統計信息"""
        input_data = TextSummarizerInput(text=sample_text, operation="stats")
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        assert result.operation == "stats"
        assert result.stats is not None
        assert "char_count" in result.stats
        assert "word_count" in result.stats
        assert "sentence_count" in result.stats
        assert result.stats["char_count"] > 0
        assert result.stats["word_count"] > 0

    @pytest.mark.asyncio
    async def test_invalid_operation(self, tool, sample_text):
        """測試無效操作"""
        input_data = TextSummarizerInput(text=sample_text, operation="invalid")
        with pytest.raises(ToolValidationError):
            await tool.execute(input_data)

    @pytest.mark.asyncio
    async def test_keywords_max_limit(self, tool, sample_text):
        """測試關鍵詞數量限制"""
        input_data = TextSummarizerInput(text=sample_text, operation="keywords", max_keywords=3)
        result = await tool.execute(input_data)

        assert len(result.keywords) <= 3

    @pytest.mark.asyncio
    async def test_summary_length(self, tool, sample_text):
        """測試摘要長度"""
        input_data = TextSummarizerInput(text=sample_text, operation="summary", summary_length=1)
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        # 摘要應該包含至少一個句子
        assert len(result.result) > 0

    @pytest.mark.asyncio
    async def test_empty_text(self, tool):
        """測試空文本"""
        input_data = TextSummarizerInput(text="", operation="stats")
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        assert result.stats is not None
        assert result.stats["char_count"] == 0
        assert result.stats["word_count"] == 0

    @pytest.mark.asyncio
    async def test_stats_multiline_text(self, tool):
        """測試多行文本統計"""
        multiline_text = "Line 1.\nLine 2.\n\nLine 3."
        input_data = TextSummarizerInput(text=multiline_text, operation="stats")
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        assert result.stats["line_count"] >= 3
        assert result.stats["paragraph_count"] >= 1

    @pytest.mark.asyncio
    async def test_operation_case_insensitive(self, tool, sample_text):
        """測試操作類型大小寫不敏感"""
        input_data = TextSummarizerInput(text=sample_text, operation="KEYWORDS")
        result = await tool.execute(input_data)

        assert isinstance(result, TextSummarizerOutput)
        assert result.keywords is not None

    @pytest.mark.asyncio
    async def test_keywords_stop_words_filtered(self, tool):
        """測試關鍵詞過濾停用詞"""
        text = "The quick brown fox jumps over the lazy dog. The dog is lazy."
        input_data = TextSummarizerInput(text=text, operation="keywords", max_keywords=10)
        result = await tool.execute(input_data)

        # 停用詞 "the", "is" 應該被過濾
        assert "the" not in result.keywords
        assert "is" not in result.keywords
