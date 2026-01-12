# 代碼功能說明: 模糊匹配器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""模糊匹配器

實現模糊匹配算法，用於在精確匹配失敗時找到最相似的目標。
"""

import re
from typing import Any, List, Optional, Tuple

try:
    from Levenshtein import distance as levenshtein_distance
except ImportError:
    # 如果 python-Levenshtein 未安裝，使用標準庫 difflib
    from difflib import SequenceMatcher

    def levenshtein_distance(s1: str, s2: str) -> int:
        """使用 SequenceMatcher 計算相似度，轉換為距離"""
        similarity = SequenceMatcher(None, s1, s2).ratio()
        # 將相似度轉換為距離（0-1 相似度轉換為 0-max_len 距離）
        max_len = max(len(s1), len(s2))
        return int(max_len * (1 - similarity))


class FuzzyMatcher:
    """模糊匹配器

    提供模糊匹配功能，用於在精確匹配失敗時找到最相似的目標。
    包含性能優化：結果緩存、搜索範圍限制、早期退出。
    """

    def __init__(
        self,
        similarity_threshold: float = 0.7,
        max_search_blocks: int = 100,
        cache_size: int = 128,
    ):
        """
        初始化模糊匹配器

        Args:
            similarity_threshold: 相似度閾值（0-1），默認 0.7
            max_search_blocks: 最大搜索 Block 數量（性能優化），默認 100
            cache_size: 緩存大小（LRU 緩存），默認 128
        """
        self.similarity_threshold = similarity_threshold
        self.max_search_blocks = max_search_blocks
        self._normalize_cache: dict[str, str] = {}  # 標準化文本緩存

    def normalize_text(self, text: str) -> str:
        """
        標準化文本（去除標點、統一大小寫、去除多餘空格）

        Args:
            text: 原始文本

        Returns:
            標準化後的文本
        """
        # 檢查緩存
        if text in self._normalize_cache:
            return self._normalize_cache[text]

        # 轉換為小寫
        normalized = text.lower()
        # 去除標點符號（保留中文字符、英文字母、數字）
        normalized = re.sub(r"[^\w\s\u4e00-\u9fff]", "", normalized)
        # 去除多餘空格
        normalized = re.sub(r"\s+", " ", normalized).strip()

        # 緩存結果（限制緩存大小）
        if len(self._normalize_cache) < 1000:  # 限制緩存大小
            self._normalize_cache[text] = normalized

        return normalized

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        計算兩個文本的相似度（0-1）

        Args:
            text1: 第一個文本
            text2: 第二個文本

        Returns:
            相似度（0-1，1 表示完全相同）
        """
        # 標準化文本
        normalized1 = self.normalize_text(text1)
        normalized2 = self.normalize_text(text2)

        # 如果標準化後完全相同，返回 1.0
        if normalized1 == normalized2:
            return 1.0

        # 計算 Levenshtein 距離
        distance = levenshtein_distance(normalized1, normalized2)
        max_len = max(len(normalized1), len(normalized2))

        if max_len == 0:
            return 1.0

        # 轉換為相似度（距離越小，相似度越高）
        similarity = 1.0 - (distance / max_len)
        return similarity

    def fuzzy_match_heading(
        self,
        target_text: str,
        target_level: Optional[int],
        blocks: List[Any],
    ) -> List[Tuple[Any, float]]:
        """
        模糊匹配 Heading Block（性能優化版本）

        Args:
            target_text: 目標標題文本
            target_level: 目標標題級別（可選）
            blocks: 候選 Block 列表

        Returns:
            匹配結果列表（(block, similarity) 元組），按相似度降序排列
        """
        results: List[Tuple[Any, float]] = []

        # 性能優化：限制搜索範圍
        search_blocks = blocks[: self.max_search_blocks]

        # 標準化目標文本（只計算一次）
        normalized_target = self.normalize_text(target_text)

        for block in search_blocks:
            # 只匹配 heading 類型的 block
            if block.block_type != "heading":
                continue

            # 如果指定了 level，只匹配相同 level 的 block
            if target_level is not None:
                # 從 block content 中提取 level（簡化實現）
                content = block.content
                if content.startswith("#"):
                    level = len(content) - len(content.lstrip("#"))
                    if level != target_level:
                        continue

            # 提取標題文本（去除 # 符號）
            heading_text = block.content.lstrip("#").strip()

            # 計算相似度（使用標準化文本）
            similarity = self._calculate_similarity_fast(normalized_target, heading_text)

            # 如果相似度達到閾值，添加到結果
            if similarity >= self.similarity_threshold:
                results.append((block, similarity))

                # 性能優化：如果找到高相似度匹配（> 0.95），提前返回
                if similarity > 0.95 and len(results) == 1:
                    return results

        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _calculate_similarity_fast(self, normalized_target: str, text: str) -> float:
        """
        快速計算相似度（使用已標準化的目標文本）

        Args:
            normalized_target: 已標準化的目標文本
            text: 待比較文本

        Returns:
            相似度（0-1）
        """
        normalized_text = self.normalize_text(text)

        # 如果標準化後完全相同，返回 1.0
        if normalized_target == normalized_text:
            return 1.0

        # 計算 Levenshtein 距離
        distance = levenshtein_distance(normalized_target, normalized_text)
        max_len = max(len(normalized_target), len(normalized_text))

        if max_len == 0:
            return 1.0

        # 轉換為相似度
        similarity = 1.0 - (distance / max_len)
        return similarity

    def fuzzy_match_anchor(
        self, target_anchor_id: str, blocks: List[Any]
    ) -> List[Tuple[Any, float]]:
        """
        模糊匹配 Anchor Block

        Args:
            target_anchor_id: 目標 anchor ID
            blocks: 候選 Block 列表

        Returns:
            匹配結果列表（(block, similarity) 元組），按相似度降序排列
        """
        results: List[Tuple[Any, float]] = []

        for block in blocks:
            # 從 block 中提取 anchor ID（簡化實現）
            # 實際實現需要從 HTML id 屬性或註解標記中提取
            # 這裡假設可以從 block 的某個屬性中獲取
            anchor_id = getattr(block, "anchor_id", None)
            if not anchor_id:
                continue

            # 計算相似度
            similarity = self.calculate_similarity(target_anchor_id, anchor_id)

            # 如果相似度達到閾值，添加到結果
            if similarity >= self.similarity_threshold:
                results.append((block, similarity))

        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def fuzzy_match_block(self, target_content: str, blocks: List[Any]) -> List[Tuple[Any, float]]:
        """
        模糊匹配 Block（基於內容）

        Args:
            target_content: 目標 Block 內容
            blocks: 候選 Block 列表

        Returns:
            匹配結果列表（(block, similarity) 元組），按相似度降序排列
        """
        results: List[Tuple[Any, float]] = []

        for block in blocks:
            # 計算相似度（基於 block 內容）
            similarity = self.calculate_similarity(target_content, block.content)

            # 如果相似度達到閾值，添加到結果
            if similarity >= self.similarity_threshold:
                results.append((block, similarity))

        # 按相似度降序排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results
