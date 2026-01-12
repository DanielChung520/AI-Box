# 代碼功能說明: Policy Engine 規則評估引擎
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Policy Engine 規則評估引擎

評估政策規則的條件表達式，支持等值、數值比較、集合包含、旗標等操作。
"""

import logging
from typing import Any, Dict, List

from agents.services.policy_engine.models import (
    Decision,
    DecisionAction,
    EffectivePolicy,
    FanInMode,
    FanInPolicy,
    Policy,
    PolicyContext,
    PolicyRule,
    ReactStateType,
    RetryPolicy,
)

logger = logging.getLogger(__name__)


class RuleEvaluator:
    """規則評估引擎"""

    def __init__(self, policy: Policy):
        """
        初始化規則評估引擎

        Args:
            policy: Policy 對象
        """
        self.policy = policy

    def evaluate(self, context: PolicyContext) -> EffectivePolicy:
        """
        評估政策規則

        Args:
            context: 政策上下文

        Returns:
            EffectivePolicy 對象
        """
        # 1. 收集符合條件的規則（按優先級排序）
        matched_rules = self._match_rules(context)

        # 2. 合併 allow/forbid（deny 優先於 allow）
        effective_allow, effective_forbid = self._merge_capabilities(matched_rules)

        # 3. 選擇決策（最高優先級的 decision）
        decision = self._select_decision(matched_rules)

        # 4. 合併重試策略和 fan-in 策略
        retry = self._merge_retry_policy(matched_rules)
        fan_in = self._merge_fan_in_policy(matched_rules)

        # 5. 記錄命中的規則（用於審計）
        rule_hits = [rule.name for rule in matched_rules]

        return EffectivePolicy(
            decision=decision,
            allow=effective_allow,
            forbid=effective_forbid,
            retry=retry,
            fan_in=fan_in,
            rule_hits=rule_hits,
        )

    def _match_rules(self, context: PolicyContext) -> List[PolicyRule]:
        """
        匹配符合條件的規則

        Args:
            context: 政策上下文

        Returns:
            符合條件的規則列表（按優先級降序排序）
        """
        matched_rules = []

        for rule in self.policy.rules:
            if self._evaluate_when(rule.when, context):
                matched_rules.append(rule)

        # 按優先級降序排序
        matched_rules.sort(key=lambda r: r.priority, reverse=True)

        return matched_rules

    def _evaluate_when(self, when: Dict[str, Any], context: PolicyContext) -> bool:
        """
        評估 when 條件表達式

        支持的條件運算：
        - 等值：`command.risk_level == "critical"`
        - 數值比較：`retry_count < 2`
        - 集合包含：`observations.any_issue_type_in: ["timeout"]`
        - 旗標：`constraints.local_only: true`

        Args:
            when: 條件表達式字典
            context: 政策上下文

        Returns:
            是否匹配
        """
        if not when:
            return True  # 空條件表示總是匹配

        for key, value in when.items():
            if not self._evaluate_condition(key, value, context):
                return False

        return True

    def _evaluate_condition(self, key: str, expected_value: Any, context: PolicyContext) -> bool:
        """
        評估單個條件

        Args:
            key: 條件鍵（支持點號分隔的路徑，如 "command.risk_level"）
            expected_value: 期望值
            context: 政策上下文

        Returns:
            是否匹配
        """
        # 解析鍵路徑
        keys = key.split(".")
        current_value = self._get_nested_value(context, keys)

        # 處理特殊條件運算
        if isinstance(expected_value, dict):
            # 支持運算符，如 {"lt": 2} 表示 < 2
            for op, op_value in expected_value.items():
                if op == "lt":
                    return current_value < op_value
                elif op == "le":
                    return current_value <= op_value
                elif op == "gt":
                    return current_value > op_value
                elif op == "ge":
                    return current_value >= op_value
                elif op == "in":
                    return current_value in op_value
                elif op == "any_issue_type_in":
                    # 特殊處理：檢查 observations 中是否有指定類型的 issue
                    if isinstance(current_value, list):
                        for obs in current_value:
                            if isinstance(obs, dict) and "issues" in obs:
                                for issue in obs["issues"]:
                                    if isinstance(issue, dict) and issue.get("type") in op_value:
                                        return True
                    return False

        # 默認等值比較
        return current_value == expected_value

    def _get_nested_value(self, obj: Any, keys: List[str]) -> Any:
        """
        獲取嵌套值

        Args:
            obj: 對象
            keys: 鍵路徑列表

        Returns:
            值
        """
        current = obj
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif hasattr(current, key):
                current = getattr(current, key)
            else:
                return None

            if current is None:
                return None

        return current

    def _merge_capabilities(self, matched_rules: List[PolicyRule]) -> tuple[List[str], List[str]]:
        """
        合併能力列表（deny 優先於 allow）

        Args:
            matched_rules: 匹配的規則列表

        Returns:
            (allow_list, forbid_list) 元組
        """
        # 從默認值開始
        allow = set(self.policy.defaults.allow)
        forbid = set(self.policy.defaults.forbid)

        # 合併規則中的能力
        for rule in matched_rules:
            then = rule.then
            if "allow" in then and "capabilities" in then["allow"]:
                allow.update(then["allow"]["capabilities"])
            if "forbid" in then and "capabilities" in then["forbid"]:
                forbid.update(then["forbid"]["capabilities"])

        # deny 優先於 allow（從 allow 中移除 forbid 中的項）
        allow = allow - forbid

        return list(allow), list(forbid)

    def _select_decision(self, matched_rules: List[PolicyRule]) -> Decision | None:
        """
        選擇決策（最高優先級的 decision）

        Args:
            matched_rules: 匹配的規則列表

        Returns:
            Decision 對象，如果沒有規則產生 decision 則返回 None
        """
        for rule in matched_rules:
            then = rule.then
            if "decision" in then:
                decision_data = then["decision"]
                return Decision(
                    action=DecisionAction(decision_data["action"]),
                    reason=decision_data.get("reason"),
                    next_state=ReactStateType(decision_data["next_state"]),
                )

        return None

    def _merge_retry_policy(self, matched_rules: List[PolicyRule]) -> RetryPolicy | None:
        """
        合併重試策略（使用第一個匹配規則的重試策略）

        Args:
            matched_rules: 匹配的規則列表

        Returns:
            RetryPolicy 對象，如果沒有規則定義重試策略則返回 None
        """
        for rule in matched_rules:
            then = rule.then
            if "retry" in then:
                retry_data = then["retry"]
                return RetryPolicy(
                    max_retry=retry_data.get("max_retry", 2),
                    backoff_sec=retry_data.get("backoff_sec", 30),
                )

        return None

    def _merge_fan_in_policy(self, matched_rules: List[PolicyRule]) -> FanInPolicy | None:
        """
        合併 fan-in 策略（使用第一個匹配規則的 fan-in 策略）

        Args:
            matched_rules: 匹配的規則列表

        Returns:
            FanInPolicy 對象，如果沒有規則定義 fan-in 策略則返回 None
        """
        for rule in matched_rules:
            then = rule.then
            if "fan_in" in then:
                fan_in_data = then["fan_in"]
                return FanInPolicy(
                    mode=FanInMode(fan_in_data.get("mode", "all")),
                    threshold=fan_in_data.get("threshold", 0.7),
                )

        return None
