# 代碼功能說明: Markdown AST 解析器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Markdown AST 解析器

實現 CommonMark + GFM 的 AST 解析、Block ID 生成和 AST 操作功能。
"""

import hashlib
from typing import Any, Dict, List, Optional

try:
    from markdown_it import MarkdownIt
    from markdown_it.tree import SyntaxTreeNode
except ImportError:
    MarkdownIt = None
    SyntaxTreeNode = None


class MarkdownBlock:
    """Markdown Block 節點

    封裝 Markdown AST 節點，包含 Block ID 和內容。
    """

    def __init__(
        self,
        block_id: str,
        node: Any,
        content: str,
        start_line: int,
        end_line: int,
        block_type: str,
    ):
        """
        初始化 Markdown Block

        Args:
            block_id: Block ID
            node: AST 節點
            content: Block 內容
            start_line: 起始行號
            end_line: 結束行號
            block_type: Block 類型（heading, paragraph, code_block 等）
        """
        self.block_id = block_id
        self.node = node
        self.content = content
        self.start_line = start_line
        self.end_line = end_line
        self.block_type = block_type

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典

        Returns:
            字典表示
        """
        return {
            "block_id": self.block_id,
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "block_type": self.block_type,
        }


class MarkdownParser:
    """Markdown AST 解析器

    提供 Markdown 解析、Block ID 生成和 AST 操作功能。
    """

    def __init__(self):
        """初始化解析器"""
        if MarkdownIt is None:
            raise ImportError("markdown-it-py 未安裝。請運行: pip install markdown-it-py")
        # 使用 GFM 擴展，但禁用 linkify（需要額外依賴）
        self.md = MarkdownIt("gfm-like").disable("linkify")
        self._blocks: List[MarkdownBlock] = []
        self._block_id_map: Dict[str, MarkdownBlock] = {}

    @staticmethod
    def generate_block_id(content: str, position: int) -> str:
        """
        生成 Block ID

        Args:
            content: Block 內容
            position: 結構位置

        Returns:
            Block ID (SHA256 前 16 字符)
        """
        data = f"{content}:{position}".encode("utf-8")
        return hashlib.sha256(data).hexdigest()[:16]

    def parse(self, markdown_text: str) -> List[MarkdownBlock]:
        """
        解析 Markdown 文本為 Block 列表

        Args:
            markdown_text: Markdown 文本

        Returns:
            Block 列表
        """
        tokens = self.md.parse(markdown_text)
        self._blocks = []
        self._block_id_map = {}

        # 簡化處理：將 tokens 轉換為 blocks
        # 實際實現需要使用 markdown-it-py 的樹形結構
        markdown_text.split("\n")
        current_line = 0

        for i, token in enumerate(tokens):
            if token.type == "heading_open":
                # 提取 heading 內容
                int(token.tag[1])  # h1 -> 1
                heading_content = ""
                heading_end_line = current_line

                # 查找對應的 heading_close
                j = i + 1
                while j < len(tokens) and tokens[j].type != "heading_close":
                    if tokens[j].type == "inline":
                        heading_content += tokens[j].content
                    j += 1

                block_id = self.generate_block_id(heading_content, i)
                block = MarkdownBlock(
                    block_id=block_id,
                    node=token,
                    content=heading_content,
                    start_line=current_line,
                    end_line=heading_end_line,
                    block_type="heading",
                )
                self._blocks.append(block)
                self._block_id_map[block_id] = block
                current_line = heading_end_line + 1

            elif token.type == "paragraph_open":
                # 提取 paragraph 內容
                para_content = ""
                para_end_line = current_line

                j = i + 1
                while j < len(tokens) and tokens[j].type != "paragraph_close":
                    if tokens[j].type == "inline":
                        para_content += tokens[j].content
                    j += 1

                block_id = self.generate_block_id(para_content, i)
                block = MarkdownBlock(
                    block_id=block_id,
                    node=token,
                    content=para_content,
                    start_line=current_line,
                    end_line=para_end_line,
                    block_type="paragraph",
                )
                self._blocks.append(block)
                self._block_id_map[block_id] = block
                current_line = para_end_line + 1

        return self._blocks

    def find_block_by_id(self, block_id: str) -> Optional[MarkdownBlock]:
        """
        通過 Block ID 查找 Block

        Args:
            block_id: Block ID

        Returns:
            MarkdownBlock 對象，如果未找到返回 None
        """
        return self._block_id_map.get(block_id)

    def find_blocks_by_heading(
        self, text: Optional[str] = None, level: Optional[int] = None, occurrence: int = 1
    ) -> List[MarkdownBlock]:
        """
        通過 heading 查找 Block

        Args:
            text: Heading 文本（可選）
            level: Heading 級別（可選）
            occurrence: 出現次數（從 1 開始）

        Returns:
            Block 列表
        """
        matches = []
        for block in self._blocks:
            if block.block_type == "heading":
                if text and block.content != text:
                    continue
                if level:
                    # 從 node 中提取 level（需要實際實現）
                    # 這裡簡化處理
                    pass
                matches.append(block)

        if occurrence > 0 and len(matches) >= occurrence:
            return [matches[occurrence - 1]]
        return matches

    def find_blocks_by_anchor(self, anchor_id: str) -> List[MarkdownBlock]:
        """
        通過 anchor 查找 Block

        Args:
            anchor_id: Anchor ID

        Returns:
            Block 列表
        """
        # 簡化實現：需要從 HTML id 或註解中提取 anchor
        # 這裡返回空列表，實際實現需要解析 HTML id 或註解
        return []

    def get_all_blocks(self) -> List[MarkdownBlock]:
        """
        獲取所有 Block

        Returns:
            所有 Block 列表
        """
        return self._blocks.copy()

    def ast_to_markdown(self, blocks: Optional[List[MarkdownBlock]] = None) -> str:
        """
        將 AST 轉換回 Markdown

        Args:
            blocks: Block 列表（如果為 None，使用所有 blocks）

        Returns:
            Markdown 文本
        """
        if blocks is None:
            blocks = self._blocks

        # 簡化實現：直接使用 block content
        # 實際實現需要重建完整的 Markdown 結構
        lines = []
        for block in blocks:
            if block.block_type == "heading":
                # 需要根據 level 添加 # 符號
                lines.append(block.content)
            else:
                lines.append(block.content)
            lines.append("")

        return "\n".join(lines)
