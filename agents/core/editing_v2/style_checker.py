# 代碼功能說明: 樣式檢查器
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""樣式檢查器

實現樣式檢查功能（語氣、術語、格式）。
"""

import re
from typing import Any, Dict, List, Optional


class StyleChecker:
    """樣式檢查器

    提供樣式檢查功能（語氣、術語、格式）。
    """

    def __init__(self, style_guide: Optional[str] = None):
        """
        初始化樣式檢查器

        Args:
            style_guide: 樣式指南名稱（如 "enterprise-tech-v1"）
        """
        self.style_guide = style_guide
        self._load_style_rules(style_guide)

    def _load_style_rules(self, style_guide: Optional[str]) -> None:
        """
        加載樣式規則

        Args:
            style_guide: 樣式指南名稱
        """
        # 簡化實現：定義基本規則
        # 實際實現應該從配置文件或數據庫加載規則
        self.rules = {
            "enterprise-tech-v1": {
                "forbid_first_person": True,  # 禁止第一人稱
                "forbid_imperative": True,  # 禁止命令式
                "required_terminology": [],  # 必需術語表（可選）
                "forbidden_terms": [],  # 禁止術語表（可選）
            }
        }

        if style_guide and style_guide in self.rules:
            self.current_rules = self.rules[style_guide]
        else:
            # 默認規則
            self.current_rules = {
                "forbid_first_person": False,
                "forbid_imperative": False,
                "required_terminology": [],
                "forbidden_terms": [],
            }

    def check(self, content: str) -> List[Dict[str, Any]]:
        """
        檢查樣式違規

        Args:
            content: 內容

        Returns:
            違規列表（每個違規包含 type、message、position、suggestion）
        """
        violations: List[Dict[str, Any]] = []

        # 語氣檢查
        violations.extend(self._check_tone(content))

        # 術語檢查
        violations.extend(self._check_terminology(content))

        # 格式檢查
        violations.extend(self._check_format(content))

        return violations

    def _check_tone(self, content: str) -> List[Dict[str, Any]]:
        """
        檢查語氣（第一人稱、命令式）

        Args:
            content: 內容

        Returns:
            違規列表
        """
        violations: List[Dict[str, Any]] = []

        # 檢查第一人稱（簡化實現）
        if self.current_rules.get("forbid_first_person", False):
            first_person_patterns = [
                r"\b我\b",
                r"\b我們\b",
                r"\bI\b",
                r"\bwe\b",
                r"\bmy\b",
                r"\bour\b",
            ]
            for pattern in first_person_patterns:
                matches = list(re.finditer(pattern, content, re.IGNORECASE))
                for match in matches:
                    violations.append(
                        {
                            "type": "tone_first_person",
                            "message": f"禁止使用第一人稱: {match.group()}",
                            "position": match.start(),
                            "suggestion": "使用第三人稱或客觀描述",
                        }
                    )

        # 檢查命令式（簡化實現）
        if self.current_rules.get("forbid_imperative", False):
            imperative_patterns = [
                r"^請\s+",  # 中文命令式
                r"^Please\s+",  # 英文命令式
                r"^必須\s+",
                r"^應該\s+",
            ]
            lines = content.split("\n")
            for line_num, line in enumerate(lines):
                for pattern in imperative_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        violations.append(
                            {
                                "type": "tone_imperative",
                                "message": f"禁止使用命令式語氣: {line[:50]}",
                                "position": line_num,
                                "suggestion": "使用陳述式語氣",
                            }
                        )

        return violations

    def _check_terminology(self, content: str) -> List[Dict[str, Any]]:
        """
        檢查術語（必需術語、禁止術語）

        Args:
            content: 內容

        Returns:
            違規列表
        """
        violations: List[Dict[str, Any]] = []

        required_terms: List[str] = self.current_rules.get("required_terminology", [])
        forbidden_terms: List[str] = self.current_rules.get("forbidden_terms", [])

        # 檢查必需術語（如果配置了）
        for term in required_terms:
            if term.lower() not in content.lower():
                violations.append(
                    {
                        "type": "terminology_missing",
                        "message": f"缺少必需術語: {term}",
                        "position": -1,
                        "suggestion": f"使用標準術語: {term}",
                    }
                )

        # 檢查禁止術語
        for term in forbidden_terms:
            matches = list(re.finditer(rf"\b{re.escape(term)}\b", content, re.IGNORECASE))
            for match in matches:
                violations.append(
                    {
                        "type": "terminology_forbidden",
                        "message": f"禁止使用術語: {term}",
                        "position": match.start(),
                        "suggestion": f"使用標準術語替代: {term}",
                    }
                )

        return violations

    def _check_format(self, content: str) -> List[Dict[str, Any]]:
        """
        檢查格式（表格標頭、列表格式等）

        Args:
            content: 內容

        Returns:
            違規列表
        """
        violations: List[Dict[str, Any]] = []

        lines = content.split("\n")

        # 檢查表格標頭（簡化實現）
        in_table = False
        for line_num, line in enumerate(lines):
            if "|" in line and line.strip().startswith("|"):
                if not in_table:
                    # 檢查下一行是否為分隔符
                    if line_num + 1 < len(lines):
                        next_line = lines[line_num + 1]
                        if "|" not in next_line or "---" not in next_line:
                            violations.append(
                                {
                                    "type": "format_table_header",
                                    "message": "表格缺少分隔符行",
                                    "position": line_num,
                                    "suggestion": "在表格標頭後添加分隔符行（| --- | --- |）",
                                }
                            )
                    in_table = True
                else:
                    # 檢查表格行格式
                    cells = [cell.strip() for cell in line.split("|") if cell.strip()]
                    if len(cells) == 0:
                        in_table = False
            else:
                in_table = False

        # 檢查列表格式（簡化實現）
        for line_num, line in enumerate(lines):
            # 檢查無序列表格式
            if line.strip().startswith("- ") or line.strip().startswith("* "):
                # 確保縮進正確
                indent = len(line) - len(line.lstrip())
                if indent > 0 and indent % 2 != 0:
                    violations.append(
                        {
                            "type": "format_list_indent",
                            "message": "列表縮進不正確",
                            "position": line_num,
                            "suggestion": "使用 2 的倍數空格縮進",
                        }
                    )

        return violations
