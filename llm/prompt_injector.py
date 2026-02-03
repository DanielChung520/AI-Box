#!/usr/bin/env python3
"""
代碼功能說明: Prompt 注入器 - 規範管理工具
創建日期: 2026-02-02
創建人: OpenCode AI
最後修改日期: 2026-02-02

功能:
  - 從 JSON 檔案載入系統規範
  - 動態注入到 LLM prompt
  - 支援開關特定規範
  - 可隨時增加/修改規範
"""

import json
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class EnforcementLevel(Enum):
    """規範強制等級"""
    HARD = "hard"
    SOFT = "soft"
    INFO = "info"


@dataclass
class Rule:
    """單一規範"""
    id: str
    name: str
    description: str
    severity: str = "info"
    enforcement: str = "soft"
    examples: Dict[str, Any] = field(default_factory=dict)
    solution: str = ""


@dataclass
class RuleCategory:
    """規範類別"""
    name: str
    description: str
    priority: str
    enabled: bool
    rules: List[Rule] = field(default_factory=list)


class PromptInjector:
    """Prompt 注入器 - 管理系統規範"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化 Prompt 注入器

        Args:
            config_path: system-prompts.json 檔案路徑
        """
        if config_path is None:
            config_path = "/home/daniel/ai-box/config/prompts/system-prompts.json"

        self.config_path = Path(config_path)
        self.system_prompts_config: Dict = {}
        self.categories: Dict[str, RuleCategory] = {}
        self._load_config()

    def _load_config(self) -> None:
        """載入配置"""
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return

        with open(self.config_path, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
            self.system_prompts_config = raw_config.get("system_prompts", raw_config)

        # 解析類別和規則
        categories_config = self.system_prompts_config.get("categories", {})

        for cat_id, cat_config in categories_config.items():
            rules = []
            for rule_data in cat_config.get("rules", []):
                rule = Rule(
                    id=rule_data.get("id", ""),
                    name=rule_data.get("name", ""),
                    description=rule_data.get("description", ""),
                    severity=rule_data.get("severity", "info"),
                    enforcement=rule_data.get("enforcement", "soft"),
                    examples=rule_data.get("examples", {}),
                    solution=rule_data.get("solution", "")
                )
                rules.append(rule)

            category = RuleCategory(
                name=cat_config.get("name", cat_id),
                description=cat_config.get("description", ""),
                priority=cat_config.get("priority", "medium"),
                enabled=cat_config.get("enabled", True),
                rules=rules
            )
            self.categories[cat_id] = category

    def get_active_categories(self) -> List[str]:
        """獲取已啟用的類別"""
        active = self.system_prompts_config.get("active_rules", {}).get("categories", [])
        if not active:
            return [cat_id for cat_id, cat in self.categories.items() if cat.enabled]
        return active

    def generate_system_prompt(self, include_categories: Optional[List[str]] = None) -> str:
        """
        生成完整的 System Prompt

        Args:
            include_categories: 要包含的類別列表 (預設: 所有啟用類別)

        Returns:
            格式化後的 system prompt
        """
        if include_categories is None:
            include_categories = self.get_active_categories()

        prompt_parts = [
            "# AI-Box 行為規範",
            "",
            "你是一個 AI 助手，請遵守以下行為規範：",
            ""
        ]

        for cat_id in include_categories:
            if cat_id not in self.categories:
                continue

            category = self.categories[cat_id]
            if not category.enabled:
                continue

            prompt_parts.append(f"## {category.name}")
            prompt_parts.append(f"{category.description}")
            prompt_parts.append("")

            for rule in category.rules:
                emoji = "🔴" if rule.enforcement == "hard" else ("🟡" if rule.enforcement == "soft" else "🟢")
                prompt_parts.append(f"{emoji} **{rule.id} {rule.name}**")
                prompt_parts.append(f"   {rule.description}")
                if rule.solution:
                    prompt_parts.append(f"   解決方式: {rule.solution}")
                prompt_parts.append("")

        prompt_parts.append("---")
        prompt_parts.append("*遵守以上規範可以獲得更好的回應品質。*")

        return "\n".join(prompt_parts)

    def get_rule_by_id(self, rule_id: str) -> Optional[Rule]:
        """根據 ID 獲取規則"""
        for category in self.categories.values():
            for rule in category.rules:
                if rule.id == rule_id:
                    return rule
        return None

    def validate_content(self, content: str) -> List[Dict]:
        """驗證內容是否符合規範"""
        violations = []

        # 檢查 Mermaid 全形標點
        fullwidth_chars = ["：", "；", "，", "＝"]
        for char in fullwidth_chars:
            if char in content:
                rule = self.get_rule_by_id("MR001")
                violations.append({
                    "rule_id": "MR001",
                    "rule_name": rule.name if rule else "全形標點",
                    "severity": "error",
                    "match": char,
                    "suggestion": "使用半形標點 : ; , ="
                })

        return violations

    def fix_content(self, content: str) -> str:
        """自動修正內容中的規範問題"""
        fixed = content
        replacements = {
            "：": ":",
            "；": ";",
            "，": ",",
            "＝": "=",
            "（": "(",
            "）": ")",
            "【": "[",
            "】": "]"
        }
        for old, new in replacements.items():
            fixed = fixed.replace(old, new)
        return fixed

    def reload(self) -> None:
        """重新載入配置"""
        self.categories.clear()
        self._load_config()

    def list_categories(self) -> List[Dict]:
        """列出所有類別"""
        return [
            {
                "id": cat_id,
                "name": cat.name,
                "description": cat.description,
                "enabled": cat.enabled,
                "priority": cat.priority,
                "rules_count": len(cat.rules)
            }
            for cat_id, cat in self.categories.items()
        ]


def create_prompt_injector() -> PromptInjector:
    """創建 Prompt 注入器實例"""
    return PromptInjector()


if __name__ == "__main__":
    injector = create_prompt_injector()

    print("=" * 60)
    print("AI-Box Prompt Injector - 測試")
    print("=" * 60)
    print()

    print("📋 已載入的規範類別:")
    for cat in injector.list_categories():
        status = "✓" if cat["enabled"] else "✗"
        print(f"  [{status}] {cat['name']} ({cat['rules_count']} 規則)")

    print()
    print("📝 System Prompt 預覽:")
    print("-" * 60)
    prompt = injector.generate_system_prompt()
    print(prompt)
    print("-" * 60)
