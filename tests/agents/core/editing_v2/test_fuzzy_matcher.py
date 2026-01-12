# 代碼功能說明: 模糊匹配器測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""模糊匹配器測試"""


from agents.core.editing_v2.fuzzy_matcher import FuzzyMatcher
from agents.core.editing_v2.markdown_parser import MarkdownBlock


class TestFuzzyMatcher:
    """模糊匹配器測試類"""

    def test_normalize_text(self):
        """測試文本標準化"""
        matcher = FuzzyMatcher()
        assert matcher.normalize_text("Hello World!") == "hello world"
        assert matcher.normalize_text("  Hello   World  ") == "hello world"
        assert matcher.normalize_text("Hello, World!") == "hello world"
        assert matcher.normalize_text("測試文本") == "測試文本"

    def test_calculate_similarity(self):
        """測試相似度計算"""
        matcher = FuzzyMatcher()
        # 完全相同
        assert matcher.calculate_similarity("hello", "hello") == 1.0
        # 相似文本
        similarity = matcher.calculate_similarity("hello", "helo")
        assert 0.5 < similarity < 1.0
        # 完全不同
        similarity = matcher.calculate_similarity("hello", "world")
        assert similarity < 0.5

    def test_fuzzy_match_heading(self):
        """測試 Heading 模糊匹配"""
        matcher = FuzzyMatcher(similarity_threshold=0.7)
        # 創建測試 blocks
        blocks = [
            MarkdownBlock(
                block_id="1",
                node=None,
                content="# Introduction",
                start_line=0,
                end_line=0,
                block_type="heading",
            ),
            MarkdownBlock(
                block_id="2",
                node=None,
                content="# Getting Started",
                start_line=1,
                end_line=1,
                block_type="heading",
            ),
            MarkdownBlock(
                block_id="3",
                node=None,
                content="This is a paragraph",
                start_line=2,
                end_line=2,
                block_type="paragraph",
            ),
        ]

        # 測試精確匹配
        results = matcher.fuzzy_match_heading("Introduction", None, blocks)
        assert len(results) > 0
        assert results[0][1] >= 0.9  # 相似度應該很高

        # 測試模糊匹配
        results = matcher.fuzzy_match_heading("Introducton", None, blocks)  # 拼寫錯誤
        assert len(results) > 0
        assert results[0][1] >= 0.7  # 相似度應該達到閾值

        # 測試 level 過濾
        results = matcher.fuzzy_match_heading("Introduction", 1, blocks)
        assert len(results) > 0

    def test_fuzzy_match_anchor(self):
        """測試 Anchor 模糊匹配"""
        matcher = FuzzyMatcher(similarity_threshold=0.7)
        # 創建測試 blocks（需要 anchor_id 屬性）
        blocks = []
        for i, anchor_id in enumerate(["intro", "getting-started", "conclusion"]):
            block = MarkdownBlock(
                block_id=str(i),
                node=None,
                content=f"Content {i}",
                start_line=i,
                end_line=i,
                block_type="heading",
            )
            block.anchor_id = anchor_id
            blocks.append(block)

        # 測試模糊匹配
        results = matcher.fuzzy_match_anchor("introduction", blocks)
        assert len(results) > 0

    def test_fuzzy_match_block(self):
        """測試 Block 模糊匹配"""
        matcher = FuzzyMatcher(similarity_threshold=0.7)
        blocks = [
            MarkdownBlock(
                block_id="1",
                node=None,
                content="This is a test paragraph",
                start_line=0,
                end_line=0,
                block_type="paragraph",
            ),
            MarkdownBlock(
                block_id="2",
                node=None,
                content="This is another paragraph",
                start_line=1,
                end_line=1,
                block_type="paragraph",
            ),
        ]

        # 測試模糊匹配
        results = matcher.fuzzy_match_block("This is a test paragrap", blocks)  # 拼寫錯誤
        assert len(results) > 0
        assert results[0][1] >= 0.7

    def test_similarity_threshold(self):
        """測試相似度閾值"""
        # 低閾值
        matcher_low = FuzzyMatcher(similarity_threshold=0.5)
        # 高閾值
        matcher_high = FuzzyMatcher(similarity_threshold=0.9)

        blocks = [
            MarkdownBlock(
                block_id="1",
                node=None,
                content="# Introduction",
                start_line=0,
                end_line=0,
                block_type="heading",
            ),
        ]

        # 低閾值應該匹配更多結果
        results_low = matcher_low.fuzzy_match_heading("Intro", None, blocks)
        results_high = matcher_high.fuzzy_match_heading("Intro", None, blocks)
        assert len(results_low) >= len(results_high)
