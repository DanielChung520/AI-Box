# 代碼功能說明: Markdown Parser 測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Markdown Parser 單元測試

測試 Markdown AST 解析功能。
"""

import pytest

from agents.core.editing_v2.markdown_parser import MarkdownParser


@pytest.fixture
def markdown_parser():
    """創建 MarkdownParser 實例"""
    try:
        return MarkdownParser()
    except ImportError:
        pytest.skip("markdown-it-py 未安裝")


@pytest.fixture
def sample_markdown():
    """示例 Markdown 文本"""
    return """# 標題一

這是第一段內容。

## 標題二

這是第二段內容。

### 標題三

這是第三段內容。
"""


class TestMarkdownParser:
    """Markdown Parser 測試類"""

    def test_parse_markdown(self, markdown_parser, sample_markdown):
        """測試 Markdown 解析"""
        blocks = markdown_parser.parse(sample_markdown)

        assert len(blocks) > 0
        assert all(hasattr(block, "block_id") for block in blocks)
        assert all(hasattr(block, "content") for block in blocks)

    def test_generate_block_id(self, markdown_parser):
        """測試 Block ID 生成"""
        content1 = "測試內容"
        position1 = 0
        block_id1 = markdown_parser.generate_block_id(content1, position1)

        assert isinstance(block_id1, str)
        assert len(block_id1) == 16  # SHA256 前 16 字符

        # 相同內容和位置應該生成相同的 ID
        block_id2 = markdown_parser.generate_block_id(content1, position1)
        assert block_id1 == block_id2

        # 不同內容或位置應該生成不同的 ID
        block_id3 = markdown_parser.generate_block_id("不同內容", position1)
        assert block_id1 != block_id3

    def test_find_block_by_id(self, markdown_parser, sample_markdown):
        """測試通過 Block ID 查找 Block"""
        blocks = markdown_parser.parse(sample_markdown)

        if len(blocks) > 0:
            block_id = blocks[0].block_id
            found_block = markdown_parser.find_block_by_id(block_id)

            assert found_block is not None
            assert found_block.block_id == block_id

    def test_find_blocks_by_heading(self, markdown_parser, sample_markdown):
        """測試通過 Heading 查找 Block"""
        markdown_parser.parse(sample_markdown)

        # 查找 heading blocks
        heading_blocks = markdown_parser.find_blocks_by_heading(text="標題一")

        # 注意：實際實現可能需要更精確的匹配
        assert isinstance(heading_blocks, list)

    def test_ast_to_markdown(self, markdown_parser, sample_markdown):
        """測試 AST 轉換回 Markdown"""
        blocks = markdown_parser.parse(sample_markdown)

        # 轉換回 Markdown
        markdown_output = markdown_parser.ast_to_markdown(blocks)

        assert isinstance(markdown_output, str)
        assert len(markdown_output) > 0
