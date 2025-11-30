# 代碼功能說明: 混合模式編排器測試
# 創建日期: 2025-11-26 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 23:30 (UTC+8)

"""測試混合模式編排器的核心功能。"""

import pytest
from agents.autogen.planner import ExecutionPlan, PlanStep, PlanStatus
from agents.workflows.base import WorkflowRequestContext
from agents.workflows.hybrid_orchestrator import (
    HybridState,
    PlanningSync,
    StateSync,
    SwitchController,
    compute_state_hash,
    deserialize_hybrid_state,
    serialize_hybrid_state,
)
from agents.workflows.langchain_graph.state import LangGraphState


class TestHybridState:
    """測試 HybridState 序列化/反序列化。"""

    def test_serialize_deserialize(self):
        """測試狀態序列化和反序列化。"""
        state: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {"key": "value"},
            "current_mode": "autogen",
            "autogen_plan": {"plan_id": "plan-1", "steps": []},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        serialized = serialize_hybrid_state(state)
        assert isinstance(serialized, str)

        deserialized = deserialize_hybrid_state(serialized)
        assert deserialized["task_id"] == state["task_id"]
        assert deserialized["task"] == state["task"]
        assert deserialized["current_mode"] == state["current_mode"]

    def test_compute_state_hash(self):
        """測試狀態哈希計算。"""
        state1: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {},
            "current_mode": "autogen",
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        state2: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {},
            "current_mode": "autogen",
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        hash1 = compute_state_hash(state1)
        hash2 = compute_state_hash(state2)
        assert hash1 == hash2

        # 修改狀態後哈希應該不同
        state2["current_mode"] = "langgraph"
        hash3 = compute_state_hash(state2)
        assert hash1 != hash3


class TestPlanningSync:
    """測試 PlanningSync 同步器。"""

    def test_autogen_to_langgraph(self):
        """測試 AutoGen 計畫轉換為 LangGraph 狀態。"""
        sync = PlanningSync()

        # 創建測試計畫
        steps = [
            PlanStep(
                step_id="step_1",
                description="步驟 1：收集資料",
                dependencies=[],
                status="completed",
                result="資料收集完成",
            ),
            PlanStep(
                step_id="step_2",
                description="步驟 2：分析資料",
                dependencies=["step_1"],
                status="pending",
            ),
        ]

        plan = ExecutionPlan(
            plan_id="plan-1",
            task="測試任務",
            steps=steps,
            status=PlanStatus.EXECUTING,
        )

        langgraph_state = sync.autogen_to_langgraph(plan)

        assert langgraph_state["task"] == plan.task
        assert len(langgraph_state["plan"]) == 2
        assert langgraph_state["plan"][0] == "步驟 1：收集資料"
        assert langgraph_state["plan"][1] == "步驟 2：分析資料"
        assert len(langgraph_state["outputs"]) == 1
        assert langgraph_state["outputs"][0] == "資料收集完成"

    def test_validate_sync(self):
        """測試同步驗證。"""
        sync = PlanningSync()

        steps = [
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                dependencies=[],
            ),
        ]

        plan = ExecutionPlan(
            plan_id="plan-1",
            task="測試任務",
            steps=steps,
        )

        langgraph_state = sync.autogen_to_langgraph(plan)
        assert sync.validate_sync(plan, langgraph_state) is True

        # 修改狀態後應該驗證失敗
        langgraph_state["plan"][0] = "不同的步驟"
        assert sync.validate_sync(plan, langgraph_state) is False


class TestStateSync:
    """測試 StateSync 同步器。"""

    def test_langgraph_to_autogen(self):
        """測試 LangGraph 狀態轉換為 AutoGen 上下文。"""
        sync = StateSync()

        state: LangGraphState = {
            "task": "測試任務",
            "context": {},
            "plan": ["步驟 1", "步驟 2"],
            "current_step": 1,
            "outputs": ["輸出 1"],
            "route": "standard",
            "status": "executing",
            "telemetry": [],
        }

        autogen_context = sync.langgraph_to_autogen(state)

        assert "execution_results" in autogen_context
        assert "plan_context" in autogen_context
        assert autogen_context["current_step"] == 1
        assert len(autogen_context["execution_results"]) == 1

    def test_update_plan_from_state(self):
        """測試從狀態更新計畫。"""
        sync = StateSync()

        steps = [
            PlanStep(
                step_id="step_1",
                description="步驟 1",
                dependencies=[],
                status="pending",
            ),
            PlanStep(
                step_id="step_2",
                description="步驟 2",
                dependencies=[],
                status="pending",
            ),
        ]

        plan = ExecutionPlan(
            plan_id="plan-1",
            task="測試任務",
            steps=steps,
        )

        state: LangGraphState = {
            "task": "測試任務",
            "context": {},
            "plan": ["步驟 1", "步驟 2"],
            "current_step": 1,
            "outputs": ["輸出 1"],
            "route": "standard",
            "status": "executing",
            "telemetry": [],
        }

        updated_plan = sync.update_plan_from_state(plan, state)

        assert updated_plan.steps[0].status == "completed"
        assert updated_plan.steps[0].result == "輸出 1"
        assert updated_plan.steps[1].status == "executing"


class TestSwitchController:
    """測試 SwitchController 切換控制器。"""

    def test_should_switch_high_error_rate(self):
        """測試高錯誤率觸發切換。"""
        controller = SwitchController()

        state: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {"fallback_modes": ["langgraph"]},
            "current_mode": "autogen",
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        metrics = {"error_rate": 0.5, "latency": 0.0, "cost": 0.0}

        target_mode = controller.should_switch("autogen", state, metrics)
        assert target_mode == "langgraph"

    def test_should_switch_cost_threshold(self):
        """測試成本超標觸發切換。"""
        controller = SwitchController()

        state: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {
                "fallback_modes": ["langgraph"],
                "cost_threshold": 100.0,
            },
            "current_mode": "autogen",
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        metrics = {
            "error_rate": 0.0,
            "latency": 0.0,
            "cost": 150.0,
            "cost_threshold": 100.0,
        }

        target_mode = controller.should_switch("autogen", state, metrics)
        assert target_mode == "langgraph"

    def test_should_switch_cooldown(self):
        """測試冷卻時間限制。"""
        controller = SwitchController(cooldown_seconds=60)

        state: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {"fallback_modes": ["langgraph"]},
            "current_mode": "autogen",
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        # 記錄一次切換
        controller.record_switch("test-task-1", "autogen", "langgraph", True)

        metrics = {"error_rate": 0.5, "latency": 0.0, "cost": 0.0}

        # 應該因為冷卻時間返回 None
        target_mode = controller.should_switch("autogen", state, metrics)
        assert target_mode is None

    def test_max_switches(self):
        """測試最大切換次數限制。"""
        controller = SwitchController(max_switches=2)

        state: HybridState = {
            "task_id": "test-task-1",
            "task": "測試任務",
            "context": {"fallback_modes": ["langgraph"]},
            "current_mode": "autogen",
            "autogen_plan": {},
            "langgraph_state": {},
            "switch_history": [],
            "sync_checkpoint": {},
            "created_at": "2025-11-26T23:00:00",
            "updated_at": "2025-11-26T23:00:00",
        }

        # 記錄兩次切換
        controller.record_switch("test-task-1", "autogen", "langgraph", True)
        controller.record_switch("test-task-1", "langgraph", "autogen", True)

        metrics = {"error_rate": 0.5, "latency": 0.0, "cost": 0.0}

        # 應該因為達到最大次數返回 None
        target_mode = controller.should_switch("autogen", state, metrics)
        assert target_mode is None


class TestHybridOrchestrator:
    """測試 HybridOrchestrator 主類。"""

    @pytest.fixture
    def request_ctx(self):
        """創建測試請求上下文。"""
        return WorkflowRequestContext(
            task_id="test-task-1",
            task="測試任務",
            context={"complexity_score": 75},
            workflow_config={
                "primary_workflow": "autogen",
                "fallback_workflows": ["langgraph"],
            },
        )

    def test_initialization(self, request_ctx):
        """測試初始化。"""
        from agents.workflows.hybrid_orchestrator import HybridOrchestrator

        orchestrator = HybridOrchestrator(
            request_ctx=request_ctx,
            primary_mode="autogen",
            fallback_modes=["langgraph"],
        )

        assert orchestrator._primary_mode == "autogen"
        assert orchestrator._fallback_modes == ["langgraph"]
        assert orchestrator._hybrid_state["task_id"] == "test-task-1"
        assert orchestrator._hybrid_state["current_mode"] == "autogen"
