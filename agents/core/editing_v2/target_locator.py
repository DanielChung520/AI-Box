# 代碼功能說明: 目標定位器（支持模糊匹配）
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""目標定位器

實現 Target Selector 的定位功能（heading、anchor、block），支持精確匹配和模糊匹配。
"""

from typing import Any, Dict

from agents.builtin.document_editing_v2.models import TargetSelector
from agents.core.editing_v2.error_handler import EditingError, EditingErrorCode, ErrorHandler
from agents.core.editing_v2.fuzzy_matcher import FuzzyMatcher
from agents.core.editing_v2.markdown_parser import MarkdownBlock, MarkdownParser


class TargetLocator:
    """目標定位器

    根據 Target Selector 定位目標 Block。
    """

    def __init__(
        self, parser: MarkdownParser, fuzzy_threshold: float = 0.7, enable_fuzzy: bool = True
    ):
        """
        初始化目標定位器

        Args:
            parser: Markdown 解析器
            fuzzy_threshold: 模糊匹配相似度閾值（0-1），默認 0.7
            enable_fuzzy: 是否啟用模糊匹配，默認 True
        """
        self.parser = parser
        self.error_handler = ErrorHandler()
        self.enable_fuzzy = enable_fuzzy
        self.fuzzy_matcher = (
            FuzzyMatcher(similarity_threshold=fuzzy_threshold) if enable_fuzzy else None
        )

    def locate(self, target_selector: TargetSelector) -> MarkdownBlock:
        """
        定位目標 Block

        Args:
            target_selector: 目標選擇器

        Returns:
            目標 MarkdownBlock

        Raises:
            EditingError: 目標未找到或模糊時拋出
        """
        selector_type = target_selector.type
        selector_data = target_selector.selector

        if selector_type == "heading":
            return self._locate_heading(selector_data)
        elif selector_type == "anchor":
            return self._locate_anchor(selector_data)
        elif selector_type == "block":
            return self._locate_block(selector_data)
        else:
            raise EditingError(
                code="INVALID_SELECTOR",
                message=f"不支持的選擇器類型: {selector_type}",
                details={"selector_type": selector_type},
            )

    def _locate_heading(self, selector_data: Dict[str, Any]) -> MarkdownBlock:
        """
        定位 Heading Block

        Args:
            selector_data: 選擇器數據

        Returns:
            Heading MarkdownBlock

        Raises:
            EditingError: 目標未找到或模糊時拋出
        """
        text = selector_data.get("text")
        level = selector_data.get("level")
        occurrence = selector_data.get("occurrence", 1)
        # path = selector_data.get("path", [])  # 後續迭代：實現 path 匹配

        # 查找匹配的 blocks（精確匹配）
        blocks = self.parser.find_blocks_by_heading(text=text, level=level, occurrence=occurrence)

        if not blocks:
            # 精確匹配失敗，嘗試模糊匹配
            if self.enable_fuzzy and self.fuzzy_matcher and text:
                # 獲取所有 heading blocks
                all_blocks = self.parser.get_all_blocks()
                fuzzy_results = self.fuzzy_matcher.fuzzy_match_heading(
                    target_text=text, target_level=level, blocks=all_blocks
                )

                if fuzzy_results:
                    # 找到模糊匹配結果
                    best_match, similarity = fuzzy_results[0]
                    # 如果只有一個匹配且相似度足夠高，直接返回
                    if len(fuzzy_results) == 1 and similarity >= 0.9:
                        return best_match
                    # 否則返回候選列表（包含相似度）
                    candidates = [
                        {
                            **block.to_dict(),
                            "similarity": sim,
                        }
                        for block, sim in fuzzy_results[:5]  # 最多返回 5 個候選
                    ]
                    raise EditingError(
                        code=EditingErrorCode.TARGET_NOT_FOUND,
                        message=f"未找到精確匹配的標題，但找到 {len(fuzzy_results)} 個相似的候選",
                        details={
                            "selector_type": "heading",
                            "selector_value": selector_data,
                            "candidates": candidates,
                        },
                        suggestions=[
                            {
                                "action": "使用模糊匹配候選",
                                "example": f"最相似的標題: {candidates[0].get('content', '')[:50]} (相似度: {candidates[0].get('similarity', 0):.2%})",
                            }
                        ],
                    )

            # 模糊匹配也失敗，拋出錯誤
            raise self.error_handler.handle_target_not_found("heading", selector_data)

        if len(blocks) > 1:
            # 如果有多個匹配，返回候選列表
            candidates = [block.to_dict() for block in blocks]
            raise self.error_handler.handle_target_ambiguous("heading", selector_data, candidates)

        return blocks[0]

    def _locate_anchor(self, selector_data: Dict[str, Any]) -> MarkdownBlock:
        """
        定位 Anchor Block

        Args:
            selector_data: 選擇器數據

        Returns:
            Anchor MarkdownBlock

        Raises:
            EditingError: 目標未找到時拋出
        """
        anchor_id = selector_data.get("anchor_id")
        if not anchor_id:
            raise EditingError(
                code="INVALID_SELECTOR",
                message="anchor_id 是必需的",
                details={"selector_data": selector_data},
            )

        blocks = self.parser.find_blocks_by_anchor(anchor_id)

        if not blocks:
            # 精確匹配失敗，嘗試模糊匹配
            if self.enable_fuzzy and self.fuzzy_matcher:
                # 獲取所有 blocks
                all_blocks = self.parser.get_all_blocks()
                fuzzy_results = self.fuzzy_matcher.fuzzy_match_anchor(
                    target_anchor_id=anchor_id, blocks=all_blocks
                )

                if fuzzy_results:
                    # 找到模糊匹配結果
                    best_match, similarity = fuzzy_results[0]
                    # 如果只有一個匹配且相似度足夠高，直接返回
                    if len(fuzzy_results) == 1 and similarity >= 0.9:
                        return best_match
                    # 否則返回候選列表
                    candidates = [
                        {
                            **block.to_dict(),
                            "similarity": sim,
                        }
                        for block, sim in fuzzy_results[:5]
                    ]
                    raise EditingError(
                        code=EditingErrorCode.TARGET_NOT_FOUND,
                        message=f"未找到精確匹配的 anchor，但找到 {len(fuzzy_results)} 個相似的候選",
                        details={
                            "selector_type": "anchor",
                            "selector_value": anchor_id,
                            "candidates": candidates,
                        },
                        suggestions=[
                            {
                                "action": "使用模糊匹配候選",
                                "example": f"最相似的 anchor: {candidates[0].get('content', '')[:50]} (相似度: {candidates[0].get('similarity', 0):.2%})",
                            }
                        ],
                    )

            # 模糊匹配也失敗，拋出錯誤
            raise self.error_handler.handle_target_not_found("anchor", anchor_id)

        if len(blocks) > 1:
            candidates = [block.to_dict() for block in blocks]
            raise self.error_handler.handle_target_ambiguous("anchor", anchor_id, candidates)

        return blocks[0]

    def _locate_block(self, selector_data: Dict[str, Any]) -> MarkdownBlock:
        """
        定位 Block（通過 Block ID）

        Args:
            selector_data: 選擇器數據

        Returns:
            MarkdownBlock

        Raises:
            EditingError: 目標未找到時拋出
        """
        block_id = selector_data.get("block_id")
        if not block_id:
            raise EditingError(
                code="INVALID_SELECTOR",
                message="block_id 是必需的",
                details={"selector_data": selector_data},
            )

        block = self.parser.find_block_by_id(block_id)

        if not block:
            raise self.error_handler.handle_target_not_found("block", block_id)

        return block
