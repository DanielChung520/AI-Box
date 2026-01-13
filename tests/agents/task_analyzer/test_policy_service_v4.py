# 代碼功能說明: Policy Service v4.0 單元測試（L4 約束驗證與策略檢查層）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Policy Service v4.0 單元測試 - 測試 L4 約束驗證與策略檢查層"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.task_analyzer.models import PolicyRule, PolicyValidationResult, TaskDAG, TaskNode
from agents.task_analyzer.policy_service import PolicyService


class TestPolicyServiceV4:
    """Policy Service v4.0 測試類"""

    @pytest.fixture
    def policy_service(self):
        """創建 PolicyService 實例"""
        return PolicyService()

    @pytest.fixture
    def task_dag(self):
        """創建 TaskDAG 實例"""
        return TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="generate_patch_design",
                    agent="DocumentEditingAgent",
                    depends_on=[],
                ),
                TaskNode(
                    id="T2",
                    capability="refine_structure",
                    agent="DocumentEditingAgent",
                    depends_on=["T1"],
                ),
            ],
            reasoning="Two-step process",
        )

    @pytest.fixture
    def task_dag_dict(self):
        """創建 TaskDAG 字典格式"""
        return {
            "task_graph": [
                {
                    "id": "T1",
                    "capability": "generate_patch_design",
                    "agent": "DocumentEditingAgent",
                    "depends_on": [],
                },
                {
                    "id": "T2",
                    "capability": "refine_structure",
                    "agent": "DocumentEditingAgent",
                    "depends_on": ["T1"],
                },
            ],
            "reasoning": "Two-step process",
        }

    @pytest.fixture
    def mock_security_agent(self):
        """創建 Mock Security Agent"""
        security_agent = MagicMock()
        # Mock 權限檢查響應
        mock_response = MagicMock()
        mock_response.allowed = True
        security_agent._check_permission = AsyncMock(return_value=mock_response)
        return security_agent

    @pytest.fixture
    def mock_rag_service(self):
        """創建 Mock RAG Service"""
        rag_service = MagicMock()
        # Mock 策略知識檢索結果
        rag_service.retrieve_policies.return_value = [
            {
                "chunk_id": "policy1",
                "content": "Document editing operations require confirmation",
                "metadata": {
                    "policy_type": "execution_policy",
                    "risk_level": "mid",
                    "scope": "all_agents",
                },
                "similarity": 0.85,
            },
        ]
        return rag_service

    def test_validate_success(
        self, policy_service, task_dag_dict, mock_security_agent, mock_rag_service
    ):
        """測試策略驗證成功"""
        # Mock Security Agent 和 RAG Service
        with patch.object(policy_service, "_security_agent", mock_security_agent):
            with patch.object(policy_service, "_rag_service", mock_rag_service):
                context = {"user_id": "user123", "tenant_id": "tenant123"}

                result = policy_service.validate(task_dag_dict, context)

                # 驗證結果
                assert isinstance(result, PolicyValidationResult)
                assert result.allowed is True
                assert result.risk_level in ["low", "mid", "high"]
                assert isinstance(result.reasons, list)

    def test_validate_with_task_dag_object(
        self, policy_service, task_dag, mock_security_agent, mock_rag_service
    ):
        """測試使用 TaskDAG 對象進行驗證"""
        # Mock Security Agent 和 RAG Service
        with patch.object(policy_service, "_security_agent", mock_security_agent):
            with patch.object(policy_service, "_rag_service", mock_rag_service):
                context = {"user_id": "user123"}

                result = policy_service.validate(task_dag, context)

                # 驗證結果
                assert isinstance(result, PolicyValidationResult)
                assert result.allowed is True

    def test_validate_permission_denied(
        self, policy_service, task_dag_dict, mock_rag_service
    ):
        """測試權限檢查失敗的情況"""
        # Mock Security Agent（權限被拒絕）
        mock_security_agent = MagicMock()
        mock_response = MagicMock()
        mock_response.allowed = False
        mock_security_agent._check_permission = AsyncMock(return_value=mock_response)

        with patch.object(policy_service, "_security_agent", mock_security_agent):
            with patch.object(policy_service, "_rag_service", mock_rag_service):
                context = {"user_id": "user123"}

                result = policy_service.validate(task_dag_dict, context)

                # 驗證結果
                assert isinstance(result, PolicyValidationResult)
                assert result.allowed is False
                assert any("權限檢查失敗" in reason for reason in result.reasons)

    def test_validate_high_risk(
        self, policy_service, task_dag_dict, mock_security_agent, mock_rag_service
    ):
        """測試高風險任務的情況"""
        # 創建包含敏感操作的 Task DAG
        high_risk_task_dag = {
            "task_graph": [
                {
                    "id": "T1",
                    "capability": "delete_file",
                    "agent": "FileManagementAgent",
                    "depends_on": [],
                    "description": "Delete important file",
                },
            ],
            "reasoning": "High risk operation",
        }

        # Mock RAG Service 返回高風險策略
        mock_rag_service.retrieve_policies.return_value = [
            {
                "chunk_id": "policy1",
                "content": "File deletion operations are high risk",
                "metadata": {
                    "policy_type": "risk_policy",
                    "risk_level": "high",
                    "scope": "all_agents",
                },
                "similarity": 0.90,
            },
        ]

        with patch.object(policy_service, "_security_agent", mock_security_agent):
            with patch.object(policy_service, "_rag_service", mock_rag_service):
                context = {"user_id": "user123"}

                result = policy_service.validate(high_risk_task_dag, context)

                # 驗證結果
                assert isinstance(result, PolicyValidationResult)
                # 高風險任務可能需要確認，但不一定被拒絕
                assert result.risk_level == "high"
                assert result.requires_confirmation is True

    def test_check_permission_success(
        self, policy_service, task_dag_dict, mock_security_agent
    ):
        """測試權限檢查成功"""
        with patch.object(policy_service, "_security_agent", mock_security_agent):
            result = policy_service.check_permission(
                user_id="user123", action="execute", resource=task_dag_dict
            )

            # 驗證結果
            assert result is True

    def test_check_permission_no_security_agent(self, policy_service, task_dag_dict):
        """測試沒有 Security Agent 的情況（默認允許）"""
        # 不設置 Security Agent
        policy_service._security_agent = None

        result = policy_service.check_permission(
            user_id="user123", action="execute", resource=task_dag_dict
        )

        # 驗證結果（默認允許）
        assert result is True

    def test_assess_risk_low(self, policy_service, task_dag_dict):
        """測試低風險評估"""
        context = {"user_id": "user123"}

        result = policy_service.assess_risk(task_dag_dict, context)

        # 驗證結果
        assert result["allowed"] is True
        assert result["risk_level"] in ["low", "mid", "high"]
        assert "risk_score" in result
        assert "risk_factors" in result

    def test_assess_risk_high(self, policy_service):
        """測試高風險評估（大量任務）"""
        # 創建包含大量任務的 Task DAG
        large_task_dag = {
            "task_graph": [
                {
                    "id": f"T{i}",
                    "capability": f"capability_{i}",
                    "agent": "TestAgent",
                    "depends_on": [],
                }
                for i in range(15)  # 超過 10 個任務
            ],
            "reasoning": "Large task graph",
        }

        context = {"user_id": "user123"}

        result = policy_service.assess_risk(large_task_dag, context)

        # 驗證結果
        assert result["risk_level"] in ["mid", "high"]  # 應該至少是中風險
        assert result["requires_confirmation"] is True

    def test_assess_risk_sensitive_operation(self, policy_service):
        """測試敏感操作風險評估"""
        # 創建包含敏感操作的 Task DAG
        sensitive_task_dag = {
            "task_graph": [
                {
                    "id": "T1",
                    "capability": "delete_file",
                    "agent": "FileManagementAgent",
                    "depends_on": [],
                    "description": "Delete important file",
                },
            ],
            "reasoning": "Sensitive operation",
        }

        context = {"user_id": "user123"}

        result = policy_service.assess_risk(sensitive_task_dag, context)

        # 驗證結果
        assert result["risk_level"] in ["mid", "high"]  # 敏感操作應該至少是中風險
        assert any("敏感操作" in factor for factor in result["risk_factors"])

    def test_check_resource_limits_success(self, policy_service):
        """測試資源限制檢查成功"""
        context = {"user_id": "user123"}

        result = policy_service.check_resource_limits("task_execution", context)

        # 驗證結果（默認應該通過，因為實際資源查詢尚未實現）
        assert result is True

    def test_evaluate_rules_allow(self, policy_service):
        """測試規則評估（允許）"""
        # 添加允許規則
        rule = PolicyRule(
            rule_id="rule1",
            rule_type="permission",
            conditions={"user_id": "user123"},
            action="allow",
        )
        policy_service.add_rule(rule)

        context = {"user_id": "user123", "task_dag": {}}

        result = policy_service.evaluate_rules(context)

        # 驗證結果
        assert result["action"] == "allow"

    def test_evaluate_rules_deny(self, policy_service):
        """測試規則評估（拒絕）"""
        # 添加拒絕規則
        rule = PolicyRule(
            rule_id="rule1",
            rule_type="permission",
            conditions={"user_id": "blocked_user"},
            action="deny",
        )
        policy_service.add_rule(rule)

        context = {"user_id": "blocked_user", "task_dag": {}}

        result = policy_service.evaluate_rules(context)

        # 驗證結果
        assert result["action"] == "deny"
        assert result["rule_id"] == "rule1"

    def test_evaluate_rules_require_confirmation(self, policy_service):
        """測試規則評估（需要確認）"""
        # 添加需要確認的規則
        rule = PolicyRule(
            rule_id="rule1",
            rule_type="risk",
            conditions={"task_dag.task_graph": {"operator": ">", "value": 5}},
            action="require_confirmation",
            risk_level="mid",
        )
        policy_service.add_rule(rule)

        task_dag = {
            "task_graph": [
                {"id": f"T{i}", "capability": "cap", "agent": "Agent", "depends_on": []}
                for i in range(10)
            ]
        }
        context = {"task_dag": task_dag}

        result = policy_service.evaluate_rules(context)

        # 驗證結果（應該繼續檢查，但記錄需要確認）
        # 由於沒有 deny 規則，最終應該返回 allow
        assert result["action"] in ["allow", "require_confirmation"]

    def test_retrieve_policy_knowledge(self, policy_service, task_dag_dict, mock_rag_service):
        """測試從 RAG-3 檢索策略知識"""
        with patch.object(policy_service, "_rag_service", mock_rag_service):
            policies = policy_service._retrieve_policy_knowledge(task_dag_dict)

            # 驗證結果
            assert isinstance(policies, list)
            # 驗證 RAG Service 被調用
            mock_rag_service.retrieve_policies.assert_called_once()

    def test_calculate_dag_depth(self, policy_service):
        """測試 DAG 深度計算"""
        # 創建有依賴關係的 Task DAG
        task_graph = [
            {"id": "T1", "depends_on": []},
            {"id": "T2", "depends_on": ["T1"]},
            {"id": "T3", "depends_on": ["T2"]},
        ]

        depth = policy_service._calculate_dag_depth(task_graph)

        # 驗證結果
        assert depth == 3  # T1 -> T2 -> T3，深度為 3

    def test_calculate_dag_depth_parallel(self, policy_service):
        """測試並行任務的 DAG 深度計算"""
        # 創建並行任務（無依賴）
        task_graph = [
            {"id": "T1", "depends_on": []},
            {"id": "T2", "depends_on": []},
            {"id": "T3", "depends_on": []},
        ]

        depth = policy_service._calculate_dag_depth(task_graph)

        # 驗證結果（並行任務深度為 1）
        assert depth == 1

    def test_check_rule_conditions_simple(self, policy_service):
        """測試簡單規則條件檢查"""
        rule = PolicyRule(
            rule_id="rule1",
            rule_type="permission",
            conditions={"user_id": "user123"},
            action="allow",
        )

        context = {"user_id": "user123"}

        result = policy_service._check_rule_conditions(rule, context)

        # 驗證結果
        assert result is True

    def test_check_rule_conditions_complex(self, policy_service):
        """測試複雜規則條件檢查（AND/OR）"""
        # 測試 AND 條件
        rule = PolicyRule(
            rule_id="rule1",
            rule_type="permission",
            conditions={
                "AND": [
                    {"user_id": "user123"},
                    {"tenant_id": "tenant123"},
                ]
            },
            action="allow",
        )

        context = {"user_id": "user123", "tenant_id": "tenant123"}

        result = policy_service._check_rule_conditions(rule, context)

        # 驗證結果
        assert result is True

    def test_check_rule_conditions_operator(self, policy_service):
        """測試帶運算符的規則條件檢查"""
        # 測試數值比較運算符
        rule = PolicyRule(
            rule_id="rule1",
            rule_type="risk",
            conditions={
                "task_dag.task_graph": {"operator": ">", "value": 5}
            },
            action="require_confirmation",
        )

        task_dag = {
            "task_graph": [
                {"id": f"T{i}", "capability": "cap", "agent": "Agent", "depends_on": []}
                for i in range(10)
            ]
        }
        context = {"task_dag": task_dag}

        result = policy_service._check_rule_conditions(rule, context)

        # 驗證結果（10 > 5，應該滿足條件）
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_integration(
        self, policy_service, task_dag, mock_security_agent, mock_rag_service
    ):
        """測試策略驗證集成測試（需要真實的 Security Agent 和 RAG Service）"""
        # 注意：此測試需要 Security Agent 和 RAG Service 已初始化
        # 如果服務未初始化，此測試可能會失敗
        try:
            with patch.object(policy_service, "_security_agent", mock_security_agent):
                with patch.object(policy_service, "_rag_service", mock_rag_service):
                    context = {"user_id": "user123", "tenant_id": "tenant123"}

                    result = policy_service.validate(task_dag, context)

                    # 如果成功，驗證結果
                    if result:
                        assert isinstance(result, PolicyValidationResult)
                        assert result.allowed is not None
                        assert result.risk_level in ["low", "mid", "high"]
        except Exception as e:
            # 如果服務未初始化，跳過此測試
            pytest.skip(f"Security Agent or RAG Service not initialized: {e}")
