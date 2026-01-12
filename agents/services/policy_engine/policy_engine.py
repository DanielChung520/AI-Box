# 代碼功能說明: Policy Engine 核心類
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Policy Engine 核心類

實現 Policy-as-Code 支持，動態熱加載政策規則，輸出符合 GRO 規範的決策。
"""

import logging
from pathlib import Path
from typing import Optional

from agents.services.policy_engine.models import EffectivePolicy, Policy, PolicyContext
from agents.services.policy_engine.policy_loader import PolicyLoader
from agents.services.policy_engine.rule_evaluator import RuleEvaluator

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Policy Engine 核心類

    實現 Policy-as-Code 支持，動態熱加載政策規則，輸出符合 GRO 規範的決策。
    """

    def __init__(self, default_policy_path: Optional[str | Path] = None):
        """
        初始化 Policy Engine

        Args:
            default_policy_path: 默認政策文件路徑（可選）
        """
        self.loader = PolicyLoader()
        self._current_policy: Optional[Policy] = None

        if default_policy_path:
            self.load_policy(default_policy_path)

    def load_policy(self, policy_path: str | Path) -> Policy:
        """
        加載政策文件

        Args:
            policy_path: 政策文件路徑

        Returns:
            Policy 對象
        """
        policy = self.loader.load_policy(policy_path)
        self._current_policy = policy
        logger.info(f"Policy loaded: {policy_path}")
        return policy

    def reload_policy(self, policy_path: str | Path) -> Policy:
        """
        重新加載政策文件（熱加載）

        Args:
            policy_path: 政策文件路徑

        Returns:
            Policy 對象
        """
        policy = self.loader.reload_policy(policy_path)
        self._current_policy = policy
        logger.info(f"Policy reloaded: {policy_path}")
        return policy

    def evaluate(self, context: PolicyContext) -> EffectivePolicy:
        """
        評估政策規則

        Args:
            context: 政策上下文

        Returns:
            EffectivePolicy 對象
        """
        if self._current_policy is None:
            logger.warning("No policy loaded, using empty policy")
            from agents.services.policy_engine.models import EffectivePolicy

            return EffectivePolicy()

        evaluator = RuleEvaluator(self._current_policy)
        return evaluator.evaluate(context)

    def get_current_policy(self) -> Optional[Policy]:
        """
        獲取當前政策

        Returns:
            Policy 對象，如果未加載則返回 None
        """
        return self._current_policy

    def check_and_reload(self, policy_path: str | Path) -> bool:
        """
        檢查並重新加載政策文件（如果已修改）

        Args:
            policy_path: 政策文件路徑

        Returns:
            是否重新加載成功
        """
        policy = self.loader.check_and_reload(policy_path)
        if policy:
            self._current_policy = policy
            return True
        return False
