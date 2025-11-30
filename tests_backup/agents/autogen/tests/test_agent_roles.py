# 代碼功能說明: AutoGen Agent 角色測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""測試 AutoGen Agent 角色定義。"""


from agents.autogen.agent_roles import (
    EvaluationAgentRole,
    ExecutionAgentRole,
    PlanningAgentRole,
    get_default_agent_roles,
)


def test_planning_agent_role():
    """測試規劃 Agent 角色。"""
    role = PlanningAgentRole()
    assert role.name == "planner"
    assert "規劃" in role.description
    assert len(role.capabilities) > 0
    assert role.max_consecutive_auto_reply == 5


def test_execution_agent_role():
    """測試執行 Agent 角色。"""
    role = ExecutionAgentRole()
    assert role.name == "executor"
    assert "執行" in role.description
    assert len(role.capabilities) > 0
    assert role.max_consecutive_auto_reply == 10


def test_evaluation_agent_role():
    """測試評估 Agent 角色。"""
    role = EvaluationAgentRole()
    assert role.name == "evaluator"
    assert "評估" in role.description
    assert len(role.capabilities) > 0
    assert role.max_consecutive_auto_reply == 5


def test_get_default_agent_roles():
    """測試獲取默認 Agent 角色。"""
    roles = get_default_agent_roles()
    assert "planner" in roles
    assert "executor" in roles
    assert "evaluator" in roles
    assert isinstance(roles["planner"], PlanningAgentRole)
    assert isinstance(roles["executor"], ExecutionAgentRole)
    assert isinstance(roles["evaluator"], EvaluationAgentRole)
