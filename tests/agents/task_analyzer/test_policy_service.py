# 代碼功能說明: Policy Service 測試用例
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Policy Service 測試用例"""

import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from agents.task_analyzer.models import PolicyRule, PolicyValidationResult, TaskDAG, TaskNode
from agents.task_analyzer.policy_service import PolicyService, get_policy_service


class TestPolicyService:
    """Policy Service 測試類"""

    @pytest.fixture
    def policy_service(self):
        """創建 Policy Service 實例"""
        return PolicyService()

    @pytest.fixture
    def simple_task_dag(self):
        """創建簡單的 Task DAG"""
        return {
            "task_graph": [
                {"id": "T1", "capability": "query", "agent": "data_agent", "depends_on": []}
            ],
            "reasoning": "簡單查詢任務",
        }

    @pytest.fixture
    def complex_task_dag(self):
        """創建複雜的 Task DAG"""
        return {
            "task_graph": [
                {"id": "T1", "capability": "query", "agent": "data_agent", "depends_on": []},
                {"id": "T2", "capability": "process", "agent": "data_agent", "depends_on": ["T1"]},
                {"id": "T3", "capability": "delete", "agent": "data_agent", "depends_on": ["T2"]},
            ],
            "reasoning": "複雜任務鏈",
        }

    def test_add_rule(self, policy_service):
        """測試添加規則"""
        rule = PolicyRule(
            rule_id="test_rule_1",
            rule_type="risk",
            conditions={"task_count": {"operator": ">", "value": 10}},
            action="require_confirmation",
            risk_level="high",
        )
        policy_service.add_rule(rule)

        rules = policy_service.list_rules()
        assert len(rules) == 1
        assert rules[0].rule_id == "test_rule_1"

    def test_remove_rule(self, policy_service):
        """測試移除規則"""
        rule = PolicyRule(
            rule_id="test_rule_1",
            rule_type="risk",
            conditions={},
            action="allow",
        )
        policy_service.add_rule(rule)

        removed = policy_service.remove_rule("test_rule_1")
        assert removed is True

        rules = policy_service.list_rules()
        assert len(rules) == 0

    def test_evaluate_rules_simple_condition(self, policy_service):
        """測試規則評估 - 簡單條件"""
        rule = PolicyRule(
            rule_id="test_rule_1",
            rule_type="risk",
            conditions={"task_count": {"operator": ">", "value": 5}},
            action="require_confirmation",
            risk_level="mid",
        )
        policy_service.add_rule(rule)

        context = {"task_count": 10}
        result = policy_service.evaluate_rules(context)

        assert result["rule_id"] == "test_rule_1"
        assert result["action"] == "require_confirmation"

    def test_evaluate_rules_and_condition(self, policy_service):
        """測試規則評估 - AND 條件"""
        rule = PolicyRule(
            rule_id="test_rule_1",
            rule_type="risk",
            conditions={
                "AND": [
                    {"task_count": {"operator": ">", "value": 5}},
                    {"has_sensitive": {"operator": "==", "value": True}},
                ]
            },
            action="deny",
            risk_level="high",
        )
        policy_service.add_rule(rule)

        context = {"task_count": 10, "has_sensitive": True}
        result = policy_service.evaluate_rules(context)

        assert result["action"] == "deny"

    def test_evaluate_rules_or_condition(self, policy_service):
        """測試規則評估 - OR 條件"""
        rule = PolicyRule(
            rule_id="test_rule_1",
            rule_type="risk",
            conditions={
                "OR": [
                    {"task_count": {"operator": ">", "value": 10}},
                    {"has_sensitive": {"operator": "==", "value": True}},
                ]
            },
            action="require_confirmation",
            risk_level="mid",
        )
        policy_service.add_rule(rule)

        context = {"task_count": 5, "has_sensitive": True}
        result = policy_service.evaluate_rules(context)

        assert result["action"] == "require_confirmation"

    def test_assess_risk_low_risk(self, policy_service, simple_task_dag):
        """測試風險評估 - 低風險"""
        result = policy_service.assess_risk(simple_task_dag)

        assert result["allowed"] is True
        assert result["risk_level"] == "low"
        assert result["requires_confirmation"] is False

    def test_assess_risk_high_risk_task_count(self, policy_service):
        """測試風險評估 - 高風險（任務數量過多）"""
        task_dag = {
            "task_graph": [{"id": f"T{i}", "capability": "query", "agent": "data_agent", "depends_on": []} for i in range(15)],
        }
        result = policy_service.assess_risk(task_dag)

        assert result["risk_level"] == "high"
        assert result["requires_confirmation"] is True
        assert "任務數量過多" in result["reason"]

    def test_assess_risk_sensitive_operation(self, policy_service, complex_task_dag):
        """測試風險評估 - 敏感操作"""
        result = policy_service.assess_risk(complex_task_dag)

        assert result["risk_level"] in ["mid", "high"]
        assert "敏感操作" in result["reason"] or "delete" in result["reason"].lower()

    def test_check_resource_limits(self, policy_service):
        """測試資源限制檢查"""
        context = {"user_id": "test_user", "tenant_id": "test_tenant"}
        result = policy_service.check_resource_limits("task_execution", context)

        # 默認應該通過（因為實際資源查詢未實現）
        assert result is True

    @patch("agents.task_analyzer.policy_service.SecurityManagerAgent")
    def test_check_permission_with_security_agent(self, mock_security_agent_class, policy_service):
        """測試權限檢查 - 有 Security Agent"""
        mock_security_agent = Mock()
        mock_response = Mock()
        mock_response.allowed = True

        async def mock_check_permission(request):
            return mock_response

        mock_security_agent._check_permission = AsyncMock(return_value=mock_response)
        policy_service._security_agent = mock_security_agent

        result = policy_service.check_permission("user123", "execute", {"task": "test"})

        assert result is True

    def test_check_permission_without_security_agent(self, policy_service):
        """測試權限檢查 - 無 Security Agent"""
        policy_service._security_agent = None

        result = policy_service.check_permission("user123", "execute", {"task": "test"})

        # 沒有 Security Agent 時，默認允許
        assert result is True

    def test_validate_simple_task(self, policy_service, simple_task_dag):
        """測試完整驗證流程 - 簡單任務"""
        context = {"user_id": "test_user"}

        result = policy_service.validate(simple_task_dag, context)

        assert isinstance(result, PolicyValidationResult)
        assert result.allowed is True
        assert result.risk_level == "low"

    def test_validate_deny_rule(self, policy_service, simple_task_dag):
        """測試完整驗證流程 - 拒絕規則"""
        # 添加拒絕規則
        rule = PolicyRule(
            rule_id="deny_rule",
            rule_type="permission",
            conditions={"user_id": {"operator": "==", "value": "blocked_user"}},
            action="deny",
        )
        policy_service.add_rule(rule)

        context = {"user_id": "blocked_user"}
        result = policy_service.validate(simple_task_dag, context)

        assert result.allowed is False
        assert len(result.reasons) > 0

    def test_calculate_dag_depth(self, policy_service):
        """測試 DAG 深度計算"""
        task_graph = [
            {"id": "T1", "depends_on": []},
            {"id": "T2", "depends_on": ["T1"]},
            {"id": "T3", "depends_on": ["T2"]},
        ]

        depth = policy_service._calculate_dag_depth(task_graph)

        assert depth == 3

    def test_calculate_dag_depth_parallel(self, policy_service):
        """測試 DAG 深度計算 - 並行任務"""
        task_graph = [
            {"id": "T1", "depends_on": []},
            {"id": "T2", "depends_on": []},
            {"id": "T3", "depends_on": ["T1", "T2"]},
        ]

        depth = policy_service._calculate_dag_depth(task_graph)

        assert depth == 2

    @patch("agents.task_analyzer.policy_service.get_rag_service")
    def test_retrieve_policy_knowledge(self, mock_get_rag_service, policy_service):
        """測試策略知識檢索"""
        mock_rag_service = Mock()
        mock_rag_service.retrieve_policies.return_value = [
            {
                "chunk_id": "policy_1",
                "content": "測試策略",
                "metadata": {"policy_type": "forbidden", "risk_level": "high"},
                "similarity": 0.9,
            }
        ]
        mock_get_rag_service.return_value = mock_rag_service
        policy_service._rag_service = mock_rag_service

        task_dag = {
            "task_graph": [{"id": "T1", "capability": "query", "agent": "data_agent"}],
        }

        knowledge = policy_service._retrieve_policy_knowledge(task_dag)

        assert len(knowledge) == 1
        assert knowledge[0]["chunk_id"] == "policy_1"

    def test_get_field_value_nested(self, policy_service):
        """測試嵌套字段值獲取"""
        context = {
            "task_dag": {
                "task_graph": [
                    {"id": "T1", "capability": "query"},
                ]
            }
        }

        value = policy_service._get_field_value("task_dag.task_graph", context)

        assert value is not None
        assert len(value) == 1

    def test_compare_values_numeric(self, policy_service):
        """測試數值比較"""
        assert policy_service._compare_values(10, 5, ">") is True
        assert policy_service._compare_values(10, 5, ">=") is True
        assert policy_service._compare_values(5, 10, "<") is True
        assert policy_service._compare_values(5, 10, "<=") is True

    def test_compare_values_string(self, policy_service):
        """測試字符串比較"""
        assert policy_service._compare_values("abc", "def", "<") is True
        assert policy_service._compare_values("def", "abc", ">") is True

    def test_evaluate_single_condition_operators(self, policy_service):
        """測試單個條件評估 - 各種運算符"""
        context = {"value": 10, "text": "hello", "list": [1, 2, 3]}

        # 相等
        assert policy_service._evaluate_single_condition({"value": 10}, context) is True

        # 大於
        assert (
            policy_service._evaluate_single_condition(
                {"value": {"operator": ">", "value": 5}}, context
            )
            is True
        )

        # 包含
        assert (
            policy_service._evaluate_single_condition(
                {"text": {"operator": "contains", "value": "ell"}}, context
            )
            is True
        )

        # in 操作
        assert (
            policy_service._evaluate_single_condition(
                {"value": {"operator": "in", "value": [1, 2, 10]}}, context
            )
            is True
        )


class TestPolicyServiceIntegration:
    """Policy Service 集成測試"""

    @pytest.fixture
    def policy_service_with_rules(self):
        """創建帶有規則的 Policy Service"""
        service = PolicyService()

        # 添加風險規則
        risk_rule = PolicyRule(
            rule_id="high_task_count",
            rule_type="risk",
            conditions={"task_dag.task_graph": {"operator": ">", "value": 10}},
            action="require_confirmation",
            risk_level="high",
        )
        service.add_rule(risk_rule)

        return service

    def test_integration_validate_with_rules(self, policy_service_with_rules):
        """測試集成驗證 - 帶規則"""
        task_dag = {
            "task_graph": [
                {"id": f"T{i}", "capability": "query", "agent": "data_agent", "depends_on": []}
                for i in range(15)
            ],
        }
        context = {"user_id": "test_user"}

        result = policy_service_with_rules.validate(task_dag, context)

        assert isinstance(result, PolicyValidationResult)
        # 由於任務數量過多，應該需要確認
        assert result.requires_confirmation is True or result.risk_level == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
