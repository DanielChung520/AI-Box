# 代碼功能說明: 原始文件偏移量到 Markdown 行的映射器
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""原始文件偏移量到 Markdown 行的映射器"""

from typing import Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class OffsetMapper:
    """管理原始文件偏移量到 Markdown 行的映射"""

    def __init__(self):
        """初始化映射器"""
        self.offset_to_line: Dict[int, int] = {}
        self.line_to_offset: Dict[int, int] = {}
        self.logger = logger.bind(component="OffsetMapper")

    def create_mapping(self, original_text: str, markdown_text: str) -> Dict[int, int]:
        """
        創建原始文件偏移量到 Markdown 行的映射

        Args:
            original_text: 原始文件文本
            markdown_text: 轉換後的 Markdown 文本

        Returns:
            映射字典，key 為原始偏移量，value 為 Markdown 行號
        """
        self.offset_to_line.clear()
        self.line_to_offset.clear()

        # 簡單映射策略：基於字符位置
        # 這是一個簡化實現，實際可能需要更複雜的算法
        original_lines = original_text.splitlines(keepends=True)
        markdown_lines = markdown_text.splitlines(keepends=True)

        original_offset = 0
        markdown_line = 1  # 行號從 1 開始

        # 嘗試建立粗略的映射關係
        for orig_line in original_lines:
            orig_line_len = len(orig_line)
            # 簡單映射：假設每行大致對應
            if markdown_line <= len(markdown_lines):
                self.offset_to_line[original_offset] = markdown_line
                self.line_to_offset[markdown_line] = original_offset
            original_offset += orig_line_len
            markdown_line += 1

        self.logger.info(
            "映射表創建完成",
            original_length=len(original_text),
            markdown_length=len(markdown_text),
            mappings=len(self.offset_to_line),
        )

        return self.offset_to_line.copy()

    def get_markdown_line(self, original_offset: int) -> Optional[int]:
        """
        根據原始偏移量獲取對應的 Markdown 行號

        Args:
            original_offset: 原始文件中的字符偏移量

        Returns:
            Markdown 行號，如果找不到則返回 None
        """
        # 找到最接近的偏移量
        if original_offset in self.offset_to_line:
            return self.offset_to_line[original_offset]

        # 查找最接近的較小偏移量
        closest_offset = None
        for offset in sorted(self.offset_to_line.keys()):
            if offset <= original_offset:
                closest_offset = offset
            else:
                break

        if closest_offset is not None:
            return self.offset_to_line[closest_offset]

        return None

    def get_original_offset(self, markdown_line: int) -> Optional[int]:
        """
        根據 Markdown 行號獲取對應的原始偏移量

        Args:
            markdown_line: Markdown 行號

        Returns:
            原始文件中的字符偏移量，如果找不到則返回 None
        """
        return self.line_to_offset.get(markdown_line)

    def get_mapping_stats(self) -> Dict[str, int]:
        """
        獲取映射統計信息

        Returns:
            包含映射統計信息的字典
        """
        return {
            "total_mappings": len(self.offset_to_line),
            "offset_to_line_count": len(self.offset_to_line),
            "line_to_offset_count": len(self.line_to_offset),
        }
