# 代碼功能說明: AutoGen Execution Planning 測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""測試 Execution Planning 功能。"""


from agents.autogen.planner import (
    ExecutionPlan,
    ExecutionPlanner,
    PlanStatus,
    PlanStep,
)


def test_plan_step():
    """測試計劃步驟。"""
    step = PlanStep(
        step_id="step_1",
        description="執行步驟 1",
        dependencies=[],
        estimated_tokens=1000,
        estimated_duration=60,
    )
    assert step.step_id == "step_1"
    assert step.status == "pending"
    assert step.retry_count == 0


def test_execution_plan():
    """測試執行計劃。"""
    steps = [
        PlanStep(
            step_id="step_1",
            description="步驟 1",
            estimated_tokens=1000,
        ),
        PlanStep(
            step_id="step_2",
            description="步驟 2",
            estimated_tokens=2000,
        ),
    ]
    plan = ExecutionPlan(
        plan_id="plan_001",
        task="測試任務",
        steps=steps,
    )
    assert plan.plan_id == "plan_001"
    assert len(plan.steps) == 2
    assert plan.total_estimated_tokens == 3000
    assert plan.status == PlanStatus.DRAFT


def test_plan_validation():
    """測試計劃驗證。"""
    planner = ExecutionPlanner()

    # 有效計劃
    valid_plan = ExecutionPlan(
        plan_id="plan_001",
        task="測試任務",
        steps=[
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                estimated_tokens=1000,
            ),
        ],
    )
    score = planner._validate_plan(valid_plan)
    assert 0.0 <= score <= 1.0

    # 無效計劃（無步驟）
    empty_plan = ExecutionPlan(
        plan_id="plan_002",
        task="測試任務",
        steps=[],
    )
    score = planner._validate_plan(empty_plan)
    assert score < 0.5
