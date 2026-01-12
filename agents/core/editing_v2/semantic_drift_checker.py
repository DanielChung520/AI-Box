# 代碼功能說明: 語義漂移檢查器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""語義漂移檢查器

實現語義漂移檢查功能（NER 變更率、關鍵詞交集比例）。
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set


class SemanticDriftChecker:
    """語義漂移檢查器

    提供語義漂移檢查功能（NER 變更率、關鍵詞交集比例）。
    """

    def __init__(
        self,
        ner_change_rate_max: float = 0.3,
        keywords_overlap_min: float = 0.5,
    ):
        """
        初始化語義漂移檢查器

        Args:
            ner_change_rate_max: NER 變更率最大值（0-1），默認 0.3
            keywords_overlap_min: 關鍵詞交集比例最小值（0-1），默認 0.5
        """
        self.ner_change_rate_max = ner_change_rate_max
        self.keywords_overlap_min = keywords_overlap_min

    def check(self, original_content: str, new_content: str) -> List[Dict[str, Any]]:
        """
        檢查語義漂移

        Args:
            original_content: 原始內容
            new_content: 新內容

        Returns:
            違規列表（每個違規包含 type、message、details、suggestion）
        """
        violations: List[Dict[str, Any]] = []

        # NER 變更率檢查
        ner_violation = self._check_ner_change_rate(original_content, new_content)
        if ner_violation:
            violations.append(ner_violation)

        # 關鍵詞交集比例檢查
        keyword_violation = self._check_keywords_overlap(original_content, new_content)
        if keyword_violation:
            violations.append(keyword_violation)

        return violations

    def _extract_entities(self, content: str) -> Set[str]:
        """
        提取命名實體（簡化實現）

        Args:
            content: 內容

        Returns:
            實體集合
        """
        # 簡化實現：提取大寫字母開頭的單詞和中文專有名詞
        # 實際實現應該使用 spaCy 或 transformers 進行 NER
        entities: Set[str] = set()

        # 提取大寫字母開頭的單詞（可能是專有名詞）
        words = re.findall(r"\b[A-Z][a-z]+\b", content)
        entities.update(words)

        # 提取中文專有名詞（簡化：提取 2-4 個中文字符的詞組）
        chinese_entities = re.findall(r"[\u4e00-\u9fff]{2,4}", content)
        entities.update(chinese_entities)

        return entities

    def _extract_keywords(self, content: str, top_n: int = 10) -> Set[str]:
        """
        提取關鍵詞（簡化實現：使用 TF-IDF 或詞頻）

        Args:
            content: 內容
            top_n: 返回前 N 個關鍵詞

        Returns:
            關鍵詞集合
        """
        # 簡化實現：使用詞頻統計
        # 實際實現應該使用 TF-IDF 或 TextRank

        # 提取單詞（英文和中文）
        words = re.findall(r"\b\w+\b|[\u4e00-\u9fff]+", content.lower())

        # 過濾停用詞（簡化實現）
        stop_words = {
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "can",
            "must",
            "的",
            "了",
            "在",
            "是",
            "我",
            "有",
            "和",
            "就",
            "不",
            "人",
            "都",
            "一",
            "一個",
            "上",
            "也",
            "很",
            "到",
            "說",
            "要",
            "去",
            "你",
            "會",
            "著",
            "沒有",
            "看",
            "好",
            "自己",
            "這",
        }

        # 計算詞頻
        word_freq = Counter(word for word in words if word not in stop_words and len(word) > 1)

        # 返回前 top_n 個關鍵詞
        top_keywords = {word for word, _ in word_freq.most_common(top_n)}
        return top_keywords

    def _check_ner_change_rate(
        self, original_content: str, new_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        檢查 NER 變更率

        Args:
            original_content: 原始內容
            new_content: 新內容

        Returns:
            違規信息（如果違規），否則返回 None
        """
        original_entities = self._extract_entities(original_content)
        new_entities = self._extract_entities(new_content)

        if not original_entities:
            return None  # 如果原始內容沒有實體，跳過檢查

        # 計算變更率
        # 變更率 = (新增實體數 + 刪除實體數) / (原始實體數 + 新實體數)
        added_entities = new_entities - original_entities
        removed_entities = original_entities - new_entities
        total_entities = len(original_entities) + len(new_entities)

        if total_entities == 0:
            return None

        change_rate = (len(added_entities) + len(removed_entities)) / total_entities

        if change_rate > self.ner_change_rate_max:
            return {
                "type": "semantic_drift_ner",
                "message": f"NER 變更率過高: {change_rate:.2%}，最大允許: {self.ner_change_rate_max:.2%}",
                "details": {
                    "change_rate": change_rate,
                    "max_allowed": self.ner_change_rate_max,
                    "added_entities": list(added_entities)[:10],  # 最多顯示 10 個
                    "removed_entities": list(removed_entities)[:10],
                },
                "suggestion": "保持原始內容中的命名實體不變，或確保變更在合理範圍內",
            }

        return None

    def _check_keywords_overlap(
        self, original_content: str, new_content: str
    ) -> Optional[Dict[str, Any]]:
        """
        檢查關鍵詞交集比例

        Args:
            original_content: 原始內容
            new_content: 新內容

        Returns:
            違規信息（如果違規），否則返回 None
        """
        original_keywords = self._extract_keywords(original_content)
        new_keywords = self._extract_keywords(new_content)

        if not original_keywords:
            return None  # 如果原始內容沒有關鍵詞，跳過檢查

        # 計算交集比例
        intersection = original_keywords & new_keywords
        union = original_keywords | new_keywords

        if len(union) == 0:
            return None

        overlap_ratio = len(intersection) / len(union)

        if overlap_ratio < self.keywords_overlap_min:
            return {
                "type": "semantic_drift_keywords",
                "message": f"關鍵詞交集比例過低: {overlap_ratio:.2%}，最小要求: {self.keywords_overlap_min:.2%}",
                "details": {
                    "overlap_ratio": overlap_ratio,
                    "min_required": self.keywords_overlap_min,
                    "original_keywords": list(original_keywords)[:10],
                    "new_keywords": list(new_keywords)[:10],
                    "intersection": list(intersection)[:10],
                },
                "suggestion": "保持原始內容中的關鍵詞，確保新內容與原始內容主題一致",
            }

        return None
