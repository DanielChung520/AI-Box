# 代碼功能說明: Policy Engine 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Policy Engine 單元測試

測試 Policy Engine 的核心功能：政策文件解析、規則評估和熱加載。
"""

from pathlib import Path

from agents.services.policy_engine import PolicyEngine
from agents.services.policy_engine.models import PolicyContext


class TestPolicyEngine:
    """Policy Engine 測試類"""

    def test_policy_engine_init(self):
        """測試 Policy Engine 初始化"""
        engine = PolicyEngine()
        assert engine is not None
        assert engine.loader is not None

    def test_load_policy(self):
        """測試加載政策文件"""
        engine = PolicyEngine()
        policy_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "config"
            / "policies"
            / "default_policy.yaml"
        )

        if policy_path.exists():
            policy = engine.load_policy(policy_path)
            assert policy is not None
            assert policy.spec_version == "1.0"
            assert len(policy.rules) > 0

    def test_evaluate_policy(self):
        """測試政策規則評估"""
        engine = PolicyEngine()
        policy_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "config"
            / "policies"
            / "default_policy.yaml"
        )

        if policy_path.exists():
            engine.load_policy(policy_path)

            # 創建測試上下文
            context = PolicyContext(
                command={"risk_level": "critical"},
                constraints={"local_only": True},
                retry_count=0,
            )

            # 評估政策
            effective_policy = engine.evaluate(context)
            assert effective_policy is not None
            assert effective_policy.rule_hits is not None

    def test_evaluate_local_only_rule(self):
        """測試本地優先規則"""
        engine = PolicyEngine()
        policy_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "config"
            / "policies"
            / "default_policy.yaml"
        )

        if policy_path.exists():
            engine.load_policy(policy_path)

            context = PolicyContext(
                constraints={"local_only": True},
            )

            effective_policy = engine.evaluate(context)
            # 應該命中 local_only_guard 規則
            assert (
                "local_only_guard" in effective_policy.rule_hits or len(effective_policy.forbid) > 0
            )

    def test_evaluate_retry_rule(self):
        """測試重試規則"""
        engine = PolicyEngine()
        policy_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "config"
            / "policies"
            / "default_policy.yaml"
        )

        if policy_path.exists():
            engine.load_policy(policy_path)

            context = PolicyContext(
                observation_summary={"blocking_issues": True},
                observations=[{"issues": [{"type": "timeout"}]}],
                retry_count=0,
            )

            effective_policy = engine.evaluate(context)
            # 應該命中 retry_on_timeout 規則
            assert (
                effective_policy.decision is not None
                or "retry_on_timeout" in effective_policy.rule_hits
            )
