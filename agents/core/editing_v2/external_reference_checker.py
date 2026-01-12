# 代碼功能說明: 外部參照檢查器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""外部參照檢查器

實現外部參照檢查功能（外部 URL、未在上下文中的事實）。
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


class ExternalReferenceChecker:
    """外部參照檢查器

    提供外部參照檢查功能（外部 URL、未在上下文中的事實）。
    """

    def __init__(self, context_content: Optional[str] = None):
        """
        初始化外部參照檢查器

        Args:
            context_content: 上下文內容（用於檢查事實是否在上下文中）
        """
        self.context_content = context_content or ""

    def check(self, content: str, no_external_reference: bool = False) -> List[Dict[str, Any]]:
        """
        檢查外部參照

        Args:
            content: 內容
            no_external_reference: 是否禁止外部參照

        Returns:
            違規列表（每個違規包含 type、message、position、suggestion）
        """
        violations: List[Dict[str, Any]] = []

        if not no_external_reference:
            return violations  # 如果不禁止外部參照，跳過檢查

        # 檢查外部 URL
        violations.extend(self._check_external_urls(content))

        # 檢查未在上下文中的事實（簡化實現）
        violations.extend(self._check_facts_not_in_context(content))

        return violations

    def _check_external_urls(self, content: str) -> List[Dict[str, Any]]:
        """
        檢查外部 URL

        Args:
            content: 內容

        Returns:
            違規列表
        """
        violations: List[Dict[str, Any]] = []

        # 匹配 URL 模式
        url_pattern = r"https?://[^\s\)]+"
        matches = list(re.finditer(url_pattern, content))

        for match in matches:
            url = match.group()
            try:
                parsed = urlparse(url)
                # 檢查是否為外部 URL（簡化實現：檢查是否有域名）
                if parsed.netloc:
                    violations.append(
                        {
                            "type": "external_url",
                            "message": f"檢測到外部 URL: {url}",
                            "position": match.start(),
                            "suggestion": "移除外部 URL 或使用內部引用",
                        }
                    )
            except Exception:
                # URL 解析失敗，跳過
                pass

        return violations

    def _check_facts_not_in_context(self, content: str) -> List[Dict[str, Any]]:
        """
        檢查未在上下文中的事實（簡化實現）

        Args:
            content: 內容

        Returns:
            違規列表
        """
        violations: List[Dict[str, Any]] = []

        # 簡化實現：檢查是否包含特定的引用模式
        # 實際實現應該使用更複雜的事實提取和匹配算法

        # 檢查引用格式（如 [1], [ref], 等）
        reference_patterns = [
            r"\[ref:\d+\]",
            r"\[引用\d+\]",
            r"\[參考\d+\]",
            r"\[來源\d+\]",
        ]

        for pattern in reference_patterns:
            matches = list(re.finditer(pattern, content))
            for match in matches:
                ref_text = match.group()
                # 檢查引用是否在上下文中（簡化實現）
                if ref_text not in self.context_content:
                    violations.append(
                        {
                            "type": "fact_not_in_context",
                            "message": f"引用未在上下文中: {ref_text}",
                            "position": match.start(),
                            "suggestion": "確保所有引用都在提供的上下文中",
                        }
                    )

        return violations
