# 代碼功能說明: AutoGen Long-horizon 任務處理測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""測試 Long-horizon 任務處理功能。"""

import pytest
import tempfile
import shutil

from agents.autogen.long_horizon import LongHorizonTaskManager
from agents.autogen.planner import ExecutionPlan, PlanStep


@pytest.fixture
def temp_checkpoint_dir():
    """臨時檢查點目錄。"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_save_and_load_checkpoint(temp_checkpoint_dir):
    """測試保存和載入檢查點。"""
    manager = LongHorizonTaskManager(checkpoint_dir=temp_checkpoint_dir)

    plan = ExecutionPlan(
        plan_id="test_plan_001",
        task="測試任務",
        steps=[
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                status="completed",
            ),
        ],
    )

    # 保存檢查點
    assert manager.save_checkpoint(plan) is True

    # 載入檢查點
    checkpoint = manager.load_checkpoint("test_plan_001")
    assert checkpoint is not None
    assert checkpoint["plan_id"] == "test_plan_001"
    assert checkpoint["task"] == "測試任務"


def test_restore_plan_from_checkpoint(temp_checkpoint_dir):
    """測試從檢查點恢復計劃。"""
    manager = LongHorizonTaskManager(checkpoint_dir=temp_checkpoint_dir)

    plan = ExecutionPlan(
        plan_id="test_plan_002",
        task="測試任務",
        steps=[
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                status="completed",
            ),
        ],
    )

    # 保存並恢復
    manager.save_checkpoint(plan)
    restored = manager.restore_plan_from_checkpoint("test_plan_002")

    assert restored is not None
    assert restored.plan_id == "test_plan_002"
    assert len(restored.steps) == 1
    assert restored.steps[0].step_id == "step_1"


def test_handle_failure():
    """測試失敗處理。"""
    manager = LongHorizonTaskManager()

    plan = ExecutionPlan(
        plan_id="test_plan_003",
        task="測試任務",
        steps=[
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                status="pending",
            ),
        ],
    )

    # 處理失敗
    should_retry = manager.handle_failure(plan, "step_1", "測試錯誤", max_retries=3)

    assert should_retry is True
    assert plan.steps[0].status == "pending"
    assert plan.steps[0].retry_count == 1


def test_check_resource_limits():
    """測試資源限制檢查。"""
    manager = LongHorizonTaskManager()

    plan = ExecutionPlan(
        plan_id="test_plan_004",
        task="測試任務",
        steps=[
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                estimated_tokens=5000,
            ),
        ],
        total_estimated_tokens=5000,
    )

    # 檢查資源限制
    within_limits, msg = manager.check_resource_limits(
        plan, budget_tokens=10000, max_rounds=10
    )

    assert within_limits is True
    assert "通過" in msg
