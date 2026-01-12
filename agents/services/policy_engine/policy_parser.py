# 代碼功能說明: Policy Engine 政策文件解析器
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Policy Engine 政策文件解析器

支持 YAML 和 JSON 格式的政策文件解析。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

import yaml

from agents.services.policy_engine.models import (
    FanInMode,
    FanInPolicy,
    Policy,
    PolicyDefaults,
    PolicyRule,
    RetryPolicy,
)

logger = logging.getLogger(__name__)


class PolicyParser:
    """政策文件解析器"""

    @staticmethod
    def parse_yaml(file_path: Path) -> Policy:
        """
        解析 YAML 政策文件

        Args:
            file_path: YAML 文件路徑

        Returns:
            Policy 對象
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return PolicyParser._parse_dict(data)

    @staticmethod
    def parse_json(file_path: Path) -> Policy:
        """
        解析 JSON 政策文件

        Args:
            file_path: JSON 文件路徑

        Returns:
            Policy 對象
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return PolicyParser._parse_dict(data)

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> Policy:
        """
        解析字典數據

        Args:
            data: 政策數據字典

        Returns:
            Policy 對象
        """
        return PolicyParser._parse_dict(data)

    @staticmethod
    def _parse_dict(data: Dict[str, Any]) -> Policy:
        """內部方法：從字典解析 Policy"""
        # 解析 defaults
        defaults_data = data.get("defaults", {})
        defaults = PolicyParser._parse_defaults(defaults_data)

        # 解析 rules
        rules_data = data.get("rules", [])
        rules = [PolicyParser._parse_rule(rule_data) for rule_data in rules_data]

        return Policy(
            spec_version=data.get("spec_version", "1.0"),
            defaults=defaults,
            rules=rules,
        )

    @staticmethod
    def _parse_defaults(data: Dict[str, Any]) -> PolicyDefaults:
        """解析默認值"""
        retry_data = data.get("retry", {})
        retry = RetryPolicy(
            max_retry=retry_data.get("max_retry", 2),
            backoff_sec=retry_data.get("backoff_sec", 30),
        )

        fan_in_data = data.get("fan_in", {})
        fan_in = FanInPolicy(
            mode=FanInMode(fan_in_data.get("mode", "all")),
            threshold=fan_in_data.get("threshold", 0.7),
        )

        return PolicyDefaults(
            retry=retry,
            fan_in=fan_in,
            allow=data.get("allow", {}).get("capabilities", []),
            forbid=data.get("forbid", {}).get("capabilities", []),
        )

    @staticmethod
    def _parse_rule(data: Dict[str, Any]) -> PolicyRule:
        """解析規則"""
        return PolicyRule(
            name=data["name"],
            priority=data.get("priority", 100),
            when=data.get("when", {}),
            then=data.get("then", {}),
        )
