# 代碼功能說明: Patch 生成器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Patch 生成器

實現 Block Patch 和 Text Patch 的生成功能。
"""

import difflib
from typing import List, Optional

from agents.builtin.document_editing_v2.models import Action, BlockPatch, BlockPatchOperation
from agents.core.editing_v2.markdown_parser import MarkdownBlock, MarkdownParser


class PatchGenerator:
    """Patch 生成器

    生成 Block Patch 和 Text Patch。
    """

    def __init__(self, parser: MarkdownParser):
        """
        初始化 Patch 生成器

        Args:
            parser: Markdown 解析器
        """
        self.parser = parser

    def generate_block_patch(
        self,
        target_block: MarkdownBlock,
        action: Action,
        new_content: Optional[str] = None,
    ) -> BlockPatch:
        """
        生成 Block Patch

        Args:
            target_block: 目標 Block
            action: 編輯操作
            new_content: 新內容（用於 update 操作）

        Returns:
            BlockPatch 對象
        """
        operations: List[BlockPatchOperation] = []

        if action.mode == "insert":
            operation = BlockPatchOperation(
                op="insert",
                block_id=None,
                content=action.content or "",
                position=action.position or "after",
            )
            operations.append(operation)

        elif action.mode == "update":
            if new_content is None:
                new_content = action.content or ""
            operation = BlockPatchOperation(
                op="update",
                block_id=target_block.block_id,
                content=new_content,
                position=None,
            )
            operations.append(operation)

        elif action.mode == "delete":
            operation = BlockPatchOperation(
                op="delete",
                block_id=target_block.block_id,
                content=None,
                position=None,
            )
            operations.append(operation)

        return BlockPatch(operations=operations)

    def generate_text_patch(self, original_markdown: str, block_patch: BlockPatch) -> str:
        """
        生成 Text Patch（unified diff 格式）

        Args:
            original_markdown: 原始 Markdown 文本
            block_patch: Block Patch

        Returns:
            Unified diff 格式的文本
        """
        # 簡化實現：需要實際應用 patch 到 markdown，然後生成 diff
        # 這裡返回一個佔位符實現
        lines = original_markdown.splitlines(keepends=True)

        # 應用 patch 操作（簡化版）
        new_lines = lines.copy()
        for operation in block_patch.operations:
            if operation.op == "insert":
                # 插入新內容
                insert_pos = len(new_lines)
                new_lines.insert(insert_pos, (operation.content or "") + "\n")
            elif operation.op == "update":
                # 更新內容（需要找到對應的行並替換）
                # 簡化實現：在末尾添加
                new_lines.append((operation.content or "") + "\n")
            elif operation.op == "delete":
                # 刪除內容（需要找到對應的行並刪除）
                # 簡化實現：不做任何操作
                pass

        new_markdown = "".join(new_lines)

        # 生成 unified diff
        diff = difflib.unified_diff(
            lines,
            new_markdown.splitlines(keepends=True),
            fromfile="original",
            tofile="modified",
            lineterm="",
        )

        return "".join(diff)

    def apply_block_patch(self, markdown: str, block_patch: BlockPatch) -> str:
        """
        應用 Block Patch 到 Markdown（用於生成 Text Patch）

        Args:
            markdown: 原始 Markdown
            block_patch: Block Patch

        Returns:
            應用 Patch 後的 Markdown
        """
        # 簡化實現：實際需要解析 markdown、定位 block、應用操作
        # 這裡返回原始 markdown
        return markdown
