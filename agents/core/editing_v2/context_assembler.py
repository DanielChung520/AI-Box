# 代碼功能說明: 上下文裝配器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""上下文裝配器

實現最小上下文策略，裝配目標 Block 和相鄰 Block（性能優化版本：支持上下文緩存）。
"""

import hashlib
from typing import Dict, List, Tuple

from agents.core.editing_v2.markdown_parser import MarkdownBlock, MarkdownParser


class ContextAssembler:
    """上下文裝配器

    根據最小上下文策略裝配上下文（性能優化版本）。
    """

    def __init__(
        self, parser: MarkdownParser, max_context_blocks: int = 5, enable_cache: bool = True
    ):
        """
        初始化上下文裝配器

        Args:
            parser: Markdown 解析器
            max_context_blocks: 最大上下文 Block 數量
            enable_cache: 是否啟用上下文緩存（性能優化），默認 True
        """
        self.parser = parser
        self.max_context_blocks = max_context_blocks
        self.enable_cache = enable_cache
        self._context_cache: Dict[Tuple[str, int], List[MarkdownBlock]] = {}  # 上下文緩存

    def assemble_context(self, target_block: MarkdownBlock) -> List[MarkdownBlock]:
        """
        裝配最小上下文（性能優化版本：支持緩存）

        Args:
            target_block: 目標 Block

        Returns:
            上下文 Block 列表（包含目標 Block 和相鄰 Block）
        """
        # 性能優化：檢查緩存
        cache_key = (target_block.block_id, self.max_context_blocks)
        if self.enable_cache and cache_key in self._context_cache:
            return self._context_cache[cache_key]

        all_blocks = self.parser._blocks
        target_index = -1

        # 查找目標 Block 的索引（性能優化：使用更高效的查找）
        for i, block in enumerate(all_blocks):
            if block.block_id == target_block.block_id:
                target_index = i
                break

        if target_index == -1:
            result = [target_block]
            # 緩存結果
            if self.enable_cache:
                self._context_cache[cache_key] = result
            return result

        # 提取相鄰 Block（上下各 2-3 個）
        context_size = min(self.max_context_blocks // 2, 3)
        start_index = max(0, target_index - context_size)
        end_index = min(len(all_blocks), target_index + context_size + 1)

        context_blocks = all_blocks[start_index:end_index]

        # 性能優化：限制上下文大小
        if len(context_blocks) > self.max_context_blocks:
            context_blocks = context_blocks[: self.max_context_blocks]

        # 緩存結果（限制緩存大小）
        if self.enable_cache:
            if len(self._context_cache) < 100:  # 限制緩存大小
                self._context_cache[cache_key] = context_blocks

        return context_blocks

    def clear_cache(self) -> None:
        """
        清除上下文緩存

        用於文檔更新後清除舊緩存。
        """
        self._context_cache.clear()

    def compute_context_digest(self, context_blocks: List[MarkdownBlock]) -> str:
        """
        計算上下文摘要（SHA-256）

        Args:
            context_blocks: 上下文 Block 列表

        Returns:
            上下文摘要（SHA-256 哈希值）
        """
        # 將所有 block 的內容和位置組合
        context_str = ""
        for block in context_blocks:
            context_str += f"{block.block_id}:{block.content}:{block.start_line}\n"

        data = context_str.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    def format_context_for_llm(self, context_blocks: List[MarkdownBlock]) -> str:
        """
        格式化上下文為 LLM 輸入格式

        Args:
            context_blocks: 上下文 Block 列表

        Returns:
            格式化的上下文字符串
        """
        lines = []
        for block in context_blocks:
            lines.append(f"Block {block.block_id} ({block.block_type}):")
            lines.append(block.content)
            lines.append("")

        return "\n".join(lines)
